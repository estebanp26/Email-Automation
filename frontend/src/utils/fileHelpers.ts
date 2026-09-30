export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Validador de tipo MIME real mediante Magic Numbers (firmas binarias)
 * - PDF: 25 50 44 46 (%PDF)
 * - PNG: 89 50 4E 47 (\x89PNG)
 * - JPEG/JPG: FF D8 FF
 */
export async function validateMagicNumber(file: File): Promise<'pdf' | 'png' | 'jpeg' | null> {
  try {
    const buffer = await file.slice(0, 8).arrayBuffer();
    const bytes = new Uint8Array(buffer);

    // PDF: %PDF (25 50 44 46)
    if (bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46) {
      return 'pdf';
    }
    // PNG: \x89PNG (89 50 4E 47)
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47) {
      return 'png';
    }
    // JPEG/JPG: \xFF\xD8\xFF
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
      return 'jpeg';
    }
  } catch (err) {
    console.warn('Error al verificar Magic Numbers binarios:', err);
  }
  return null;
}

/**
 * Evaluación preliminar de legibilidad en cliente sin IA
 */
export async function evaluateLegibility(
  file: File,
  detectedType: 'pdf' | 'png' | 'jpeg'
): Promise<{ legibility: 'optimal' | 'standard' | 'warning'; reason: string }> {
  if (detectedType === 'pdf') {
    if (file.size < 1024) {
      return {
        legibility: 'warning',
        reason: 'El documento pesa menos de 1 KB; verifica que no esté vacío.',
      };
    }
    return {
      legibility: 'optimal',
      reason: 'Estructura PDF válida con peso adecuado para lectura.',
    };
  }

  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const width = img.naturalWidth;
      const height = img.naturalHeight;

      if (width < 300 || height < 300) {
        resolve({
          legibility: 'warning',
          reason: `Baja resolución (${width}x${height}px). El texto podría no ser legible.`,
        });
      } else if (width >= 800 || height >= 800) {
        resolve({
          legibility: 'optimal',
          reason: `Resolución HD (${width}x${height}px). Nitidez óptima garantizada.`,
        });
      } else {
        resolve({
          legibility: 'standard',
          reason: `Resolución estándar (${width}x${height}px).`,
        });
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve({
        legibility: 'warning',
        reason: 'No se pudieron verificar las dimensiones de la imagen.',
      });
    };
    img.src = url;
  });
}
