import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Send, FileEdit, Trash, Reply, Inbox, Paperclip, User, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';

export default function Requests() {
  const [activeFolder, setActiveFolder] = useState<'inbox' | 'sent' | 'drafts'>('inbox');
  const [requests, setRequests] = useState<any[]>([]);
  const [sentEmails, setSentEmails] = useState<any[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<any | null>(null);
  
  // Composing state
  const [isComposing, setIsComposing] = useState(false);
  const [composeData, setComposeData] = useState({ to: '', subject: '', body: '' });
  const [isSending, setIsSending] = useState(false);
  const [showToast, setShowToast] = useState(false);

  useEffect(() => {
    api.getRequests().then(data => {
      setRequests(data);
    });
  }, []);

  const handleSelectEmail = (email: any) => {
    setSelectedEmail(email);
    setIsComposing(false);
  };

  const handleReply = () => {
    if (!selectedEmail) return;
    setComposeData({
      to: selectedEmail.emailInfo?.senderEmail || selectedEmail.to,
      subject: `Re: ${selectedEmail.emailInfo?.subject || selectedEmail.subject}`,
      body: `\n\n--- Mensaje original ---\nDe: ${selectedEmail.emailInfo?.senderEmail || selectedEmail.to}\nAsunto: ${selectedEmail.emailInfo?.subject || selectedEmail.subject}`
    });
    setIsComposing(true);
  };

  const handleComposeNew = () => {
    setSelectedEmail(null);
    setComposeData({ to: '', subject: '', body: '' });
    setIsComposing(true);
  };

  const handleSendEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSending(true);
    // Simular envío
    await new Promise(r => setTimeout(r, 1200));
    
    const newSentEmail = {
      id: `sent-${Date.now()}`,
      to: composeData.to,
      subject: composeData.subject,
      body: composeData.body,
      date: new Date().toISOString(),
    };
    
    setSentEmails([newSentEmail, ...sentEmails]);
    setIsSending(false);
    setIsComposing(false);
    setSelectedEmail(newSentEmail);
    setActiveFolder('sent');
    
    // Show success toast
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  // Get active list to render
  const activeList = activeFolder === 'inbox' ? requests : activeFolder === 'sent' ? sentEmails : [];

  return (
    <div className="h-[calc(100vh-6rem)] flex gap-4 overflow-hidden">
      
      {/* 1. SIDEBAR DE CARPETAS (Paneles Izquierdos) */}
      <div className="w-[240px] flex-shrink-0 flex flex-col gap-4">
        <button
          onClick={handleComposeNew}
          className="w-full bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-90 text-white rounded-[16px] py-4 px-4 flex items-center justify-center gap-2 font-bold shadow-[0_8px_20px_rgba(99,59,255,0.25)] transition-all"
        >
          <FileEdit size={18} /> Redactar
        </button>

        <div className="bg-white border border-[#E2E8F0] rounded-[24px] p-3 flex-1 flex flex-col shadow-sm">
          <div className="space-y-1">
            <FolderButton 
              active={activeFolder === 'inbox'} 
              onClick={() => setActiveFolder('inbox')} 
              icon={<Inbox size={18} />} 
              label="Bandeja" 
              count={requests.length} 
            />
            <FolderButton 
              active={activeFolder === 'sent'} 
              onClick={() => setActiveFolder('sent')} 
              icon={<Send size={18} />} 
              label="Enviados" 
              count={sentEmails.length} 
            />
            <FolderButton 
              active={activeFolder === 'drafts'} 
              onClick={() => setActiveFolder('drafts')} 
              icon={<FileEdit size={18} />} 
              label="Borradores" 
              count={0} 
            />
          </div>
        </div>
      </div>

      {/* 2. LISTA DE CORREOS (Panel Central) */}
      <div className="w-[380px] flex-shrink-0 bg-white border border-[#E2E8F0] rounded-[24px] shadow-sm flex flex-col overflow-hidden">
        <div className="p-5 border-b border-[#E2E8F0] bg-gray-50/50">
          <h2 className="text-[18px] font-bold text-[#111827] capitalize">
            {activeFolder === 'inbox' ? 'Bandeja de Entrada' : activeFolder === 'sent' ? 'Enviados' : 'Borradores'}
          </h2>
          <p className="text-sm text-[#7C8499]">{activeList.length} correos</p>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {activeList.map((item) => {
            const isSelected = selectedEmail?.id === item.id && !isComposing;
            const subject = item.emailInfo?.subject || item.subject;
            const sender = item.emailInfo?.senderName || item.to;
            const date = new Date(item.emailInfo?.date || item.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
            const snippet = item.emailInfo?.body || item.body;

            return (
              <div 
                key={item.id} 
                onClick={() => handleSelectEmail(item)}
                className={`p-4 border-b border-[#E2E8F0] cursor-pointer transition-colors ${
                  isSelected ? 'bg-[#F2F0FF] border-l-4 border-l-[#5B3FF5]' : 'bg-white hover:bg-gray-50 border-l-4 border-l-transparent'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className={`font-bold text-[14px] truncate pr-2 ${isSelected ? 'text-[#5B3FF5]' : 'text-[#111827]'}`}>
                    {sender}
                  </span>
                  <span className="text-[11px] text-[#A3AAC2] whitespace-nowrap">{date}</span>
                </div>
                <h4 className="text-[13px] font-semibold text-[#17203A] mb-1 truncate">{subject}</h4>
                <p className="text-[12px] text-[#7C8499] line-clamp-2 leading-relaxed">{snippet}</p>
              </div>
            );
          })}
          {activeList.length === 0 && (
            <div className="p-8 text-center text-[#A3AAC2]">
              <Mail size={40} className="mx-auto mb-3 opacity-20" />
              <p>No hay correos aquí.</p>
            </div>
          )}
        </div>
      </div>

      {/* 3. VISOR / EDITOR (Panel Derecho) */}
      <div className="flex-1 bg-white border border-[#E2E8F0] rounded-[24px] shadow-sm flex flex-col overflow-hidden relative">
        
        {/* Notificación Toast */}
        <AnimatePresence>
          {showToast && (
            <motion.div 
              initial={{ opacity: 0, y: -20 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0, y: -20 }}
              className="absolute top-6 left-1/2 -translate-x-1/2 z-50 bg-[#20B486] text-white px-6 py-3 rounded-full font-bold shadow-lg flex items-center gap-2"
            >
              <CheckCircle2 size={18} /> Mensaje enviado
            </motion.div>
          )}
        </AnimatePresence>

        {isComposing ? (
          /* VISTA DE REDACCION */
          <div className="flex flex-col h-full">
            <div className="p-5 border-b border-[#E2E8F0] flex justify-between items-center bg-gray-50/50">
              <h2 className="text-[18px] font-bold text-[#111827]">Nuevo Mensaje</h2>
              <button onClick={() => setIsComposing(false)} className="text-[#A3AAC2] hover:text-red-500 transition-colors">
                <Trash size={18} />
              </button>
            </div>
            
            <form onSubmit={handleSendEmail} className="flex-1 flex flex-col p-6 gap-4 overflow-y-auto">
              <div className="flex items-center border-b border-[#E2E8F0] pb-2">
                <span className="text-[#A3AAC2] font-semibold w-16 text-sm">Para:</span>
                <input 
                  type="email" 
                  required
                  value={composeData.to}
                  onChange={e => setComposeData({...composeData, to: e.target.value})}
                  className="flex-1 focus:outline-none text-[#111827] text-[15px]" 
                  placeholder="estudiante@ejemplo.com"
                />
              </div>
              <div className="flex items-center border-b border-[#E2E8F0] pb-2">
                <span className="text-[#A3AAC2] font-semibold w-16 text-sm">Asunto:</span>
                <input 
                  type="text" 
                  required
                  value={composeData.subject}
                  onChange={e => setComposeData({...composeData, subject: e.target.value})}
                  className="flex-1 focus:outline-none text-[#111827] text-[15px]" 
                  placeholder="Asunto del correo"
                />
              </div>
              <textarea 
                required
                value={composeData.body}
                onChange={e => setComposeData({...composeData, body: e.target.value})}
                className="flex-1 mt-4 focus:outline-none text-[#17203A] text-[15px] resize-none leading-relaxed"
                placeholder="Escribe tu mensaje aquí..."
              />
              
              <div className="pt-4 flex justify-between items-center border-t border-[#E2E8F0]">
                <button type="button" className="text-[#A3AAC2] hover:text-[#5B3FF5] p-2 rounded-full transition-colors">
                  <Paperclip size={20} />
                </button>
                <button 
                  type="submit" 
                  disabled={isSending}
                  className="bg-[#5B3FF5] hover:bg-[#4A2FE0] text-white px-8 py-2.5 rounded-[12px] font-bold flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  {isSending ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <><Send size={16} /> Enviar</>
                  )}
                </button>
              </div>
            </form>
          </div>
        ) : selectedEmail ? (
          /* VISTA DE LECTURA */
          <div className="flex flex-col h-full">
            <div className="p-6 border-b border-[#E2E8F0] flex justify-between items-start bg-gray-50/30">
              <div>
                <h2 className="text-[22px] font-bold text-[#111827] mb-4">
                  {selectedEmail.emailInfo?.subject || selectedEmail.subject}
                </h2>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#5B3FF5] to-blue-400 flex items-center justify-center text-white font-bold">
                    {(selectedEmail.emailInfo?.senderName || selectedEmail.to || 'A')[0]}
                  </div>
                  <div>
                    <p className="font-bold text-[14px] text-[#111827]">
                      {selectedEmail.emailInfo?.senderName || (activeFolder === 'sent' ? 'Yo (Admin)' : selectedEmail.to)}
                    </p>
                    <p className="text-[12px] text-[#7C8499]">
                      {activeFolder === 'sent' ? `Para: ${selectedEmail.to}` : `<${selectedEmail.emailInfo?.senderEmail}>`}
                    </p>
                  </div>
                </div>
              </div>
              <p className="text-sm text-[#A3AAC2]">
                {new Date(selectedEmail.emailInfo?.date || selectedEmail.date).toLocaleString('es-ES')}
              </p>
            </div>
            
            <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
              <div className="prose prose-sm max-w-none text-[#17203A] whitespace-pre-wrap leading-relaxed">
                {selectedEmail.emailInfo?.body || selectedEmail.body}
              </div>

              {/* Adjuntos simulados */}
              {selectedEmail.emailInfo?.attachments && (
                <div className="mt-8 pt-6 border-t border-[#E2E8F0]">
                  <p className="text-sm font-bold text-[#7C8499] mb-3">Adjuntos</p>
                  <div className="flex gap-3">
                    {selectedEmail.emailInfo.attachments.map((att: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 border border-[#E2E8F0] p-2 pr-4 rounded-lg hover:bg-gray-50 cursor-pointer">
                        <div className="w-8 h-8 bg-red-100 text-red-500 rounded flex items-center justify-center">
                          <Paperclip size={16} />
                        </div>
                        <span className="text-sm font-medium text-[#111827]">{att.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Caja de Análisis de IA (solo en Inbox de solicitudes) */}
              {activeFolder === 'inbox' && selectedEmail.decision && (
                <div className="mt-10 p-5 bg-[#F2F0FF] border border-[#5B3FF5]/20 rounded-2xl">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 rounded bg-[#5B3FF5] flex items-center justify-center text-white">
                      <User size={14} />
                    </div>
                    <span className="font-bold text-[#5B3FF5]">Análisis de IA HSE</span>
                  </div>
                  <p className="text-sm text-[#17203A] mb-2">{selectedEmail.decision.reasoning}</p>
                  <p className="text-xs text-[#7C8499] font-medium">
                    Nivel de Confianza: {(selectedEmail.decision.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              )}
            </div>

            <div className="p-5 border-t border-[#E2E8F0] bg-gray-50/50">
              <button 
                onClick={handleReply}
                className="bg-white border border-[#E2E8F0] hover:bg-gray-50 text-[#17203A] px-6 py-2.5 rounded-[12px] font-bold flex items-center gap-2 transition-colors shadow-sm"
              >
                <Reply size={16} /> Responder a este correo
              </button>
            </div>
          </div>
        ) : (
          /* VISTA VACIA */
          <div className="flex-1 flex flex-col items-center justify-center text-[#A3AAC2] p-8 text-center">
            <Mail size={64} className="mb-4 opacity-20" />
            <h3 className="text-xl font-bold text-[#111827] mb-2">Ningún mensaje seleccionado</h3>
            <p className="max-w-[300px]">Selecciona un correo de la lista a la izquierda para leerlo o haz clic en "Redactar" para crear uno nuevo.</p>
          </div>
        )}
      </div>
      
    </div>
  );
}

// Componente auxiliar para botones de la barra lateral
function FolderButton({ active, onClick, icon, label, count }: { active: boolean, onClick: () => void, icon: any, label: string, count: number }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between p-3 rounded-[12px] transition-colors ${
        active 
          ? 'bg-[#F2F0FF] text-[#5B3FF5] font-bold' 
          : 'hover:bg-gray-50 text-[#7C8499] font-medium'
      }`}
    >
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-[14px]">{label}</span>
      </div>
      {count > 0 && (
        <span className={`text-[11px] px-2 py-0.5 rounded-full ${active ? 'bg-[#5B3FF5] text-white' : 'bg-gray-100 text-[#111827]'}`}>
          {count}
        </span>
      )}
    </button>
  );
}
