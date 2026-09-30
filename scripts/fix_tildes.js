const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

const sqlPath = path.resolve(__dirname, '..', 'init_database.sql');
const content = fs.readFileSync(sqlPath, 'utf8');

const startIdx = content.indexOf('INSERT INTO public.coders');
const endIdx = content.indexOf('ON CONFLICT (cedula) DO NOTHING;', startIdx);

if (startIdx === -1 || endIdx === -1) {
  console.error('Could not find coders insert block in init_database.sql');
  process.exit(1);
}

const block = content.slice(startIdx, endIdx);
const lines = block.split('\n');

let sqlUpdates = 'SET client_encoding = \'UTF8\';\n\n';
sqlUpdates += "UPDATE hse_users SET full_name = 'Laura Psicóloga HSE' WHERE email = 'laura.hse@riwi.io';\n";
sqlUpdates += "UPDATE hse_users SET full_name = 'Andrés Team Leader' WHERE email = 'andres.lead@riwi.io';\n";
sqlUpdates += "UPDATE hse_users SET full_name = 'Administrador General HSE' WHERE email = 'admin.hse@riwi.io';\n\n";

let count = 0;
for (const line of lines) {
  const m = line.match(/\(\s*'(\d+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'/);
  if (m) {
    const cedula = m[1];
    const fullName = m[2].replace(/'/g, "''");
    const route = m[4].replace(/'/g, "''");
    sqlUpdates += `UPDATE coders SET full_name = '${fullName}', route = '${route}' WHERE cedula = '${cedula}';\n`;
    count++;
  }
}

const outPath = path.resolve(__dirname, '..', 'fix_coders_utf8.sql');
fs.writeFileSync(outPath, sqlUpdates, 'utf8');
console.log(`Generated fix_coders_utf8.sql with ${count} coder updates`);

try {
  // Execute via docker
  execSync(`docker exec -i hse-postgres psql -U hse_admin -d hse_email_automation`, {
    input: fs.readFileSync(outPath),
    stdio: ['pipe', 'inherit', 'inherit']
  });
  console.log('Successfully updated PostgreSQL coders with clean UTF-8 accent marks and tildes!');
  fs.unlinkSync(outPath);
} catch (e) {
  console.error('Error updating postgres:', e.message);
}
