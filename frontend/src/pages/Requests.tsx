import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, Send, FileEdit, Trash, Reply, Inbox, Paperclip, User, 
  CheckCircle2, XCircle, AlertCircle, Zap,
  Calendar, ShieldCheck, MessageSquare, AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { getN8nConfig } from '../services/n8n';

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
  const [toastMessage, setToastMessage] = useState('Mensaje enviado');

  // n8n Manual Resolution State
  const [hseNotes, setHseNotes] = useState('');
  const [excuseType, setExcuseType] = useState('inasistencia_medica');
  const [startDate, setStartDate] = useState('');
  const [isResolving, setIsResolving] = useState(false);
  const [resolutionStatus, setResolutionStatus] = useState<{
    type: 'success' | 'warning' | 'error';
    message: string;
    details?: string;
  } | null>(null);

  // Listas derivadas: Bandeja (pendientes por resolver) vs Enviados (respondidos / resueltos)
  const inboxList = requests.filter(r => !r.hasHumanIntervention && !r.hseDecision && !r.isResponded);
  const resolvedRequests = requests.filter(r => r.hasHumanIntervention || r.hseDecision || r.isResponded);
  const sentList = [...resolvedRequests, ...sentEmails];
  const activeList = activeFolder === 'inbox' ? inboxList : activeFolder === 'sent' ? sentList : [];

  useEffect(() => {
    api.getRequests().then(data => {
      setRequests(data);
      const pending = data.filter((r: any) => !r.hasHumanIntervention && !r.hseDecision && !r.isResponded);
      if (pending.length > 0) {
        handleSelectEmail(pending[0]);
      } else if (data.length > 0) {
        handleSelectEmail(data[0]);
      }
    });
  }, []);

  const handleFolderChange = (folder: 'inbox' | 'sent' | 'drafts') => {
    setActiveFolder(folder);
    setIsComposing(false);
    setResolutionStatus(null);
    const targetList = folder === 'inbox' ? inboxList : folder === 'sent' ? sentList : [];
    if (targetList.length > 0) {
      handleSelectEmail(targetList[0]);
    } else {
      setSelectedEmail(null);
    }
  };

  const handleSelectEmail = (email: any) => {
    setSelectedEmail(email);
    setIsComposing(false);
    setResolutionStatus(null);
    setHseNotes(email.decision?.reasoning || '');
    const dateStr = email.emailInfo?.date 
      ? new Date(email.emailInfo.date).toISOString().split('T')[0] 
      : new Date().toISOString().split('T')[0];
    setStartDate(dateStr);
  };

  const handleReply = () => {
    if (!selectedEmail) return;
    setComposeData({
      to: selectedEmail.emailInfo?.senderEmail || selectedEmail.to,
      subject: `Re: ${selectedEmail.emailInfo?.subject || selectedEmail.subject}`,
      body: `\n\n--- Mensaje original ---\nDe: ${selectedEmail.emailInfo?.senderEmail || selectedEmail.to}\nAsunto: ${selectedEmail.emailInfo?.subject || selectedEmail.subject}`,
      replyToId: selectedEmail.id
    } as any);
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
    await new Promise(r => setTimeout(r, 800));
    
    const replyingId = (composeData as any).replyToId;
    const newSentEmail = {
      id: `sent-${Date.now()}`,
      to: composeData.to,
      subject: composeData.subject,
      body: composeData.body,
      date: new Date().toISOString(),
      status: 'approved',
      hasHumanIntervention: true,
      hseDecision: 'RESPONDED',
      isResponded: true,
      decision: {
        source: 'human',
        confidence: 1.0,
        reasoning: composeData.body,
        modifiedBy: 'Paola Admin (HSE)',
        modifiedAt: new Date().toISOString(),
      },
      emailInfo: {
        senderName: composeData.to,
        senderEmail: composeData.to,
        subject: composeData.subject,
        body: composeData.body,
        date: new Date().toISOString(),
      }
    };
    
    if (replyingId) {
      setRequests(prev => prev.map(r => r.id === replyingId ? {
        ...r,
        hasHumanIntervention: true,
        hseDecision: 'RESPONDED',
        isResponded: true,
        decision: {
          ...r.decision,
          source: 'human',
          reasoning: composeData.body,
          modifiedBy: 'Paola Admin (HSE)',
          modifiedAt: new Date().toISOString(),
        }
      } : r));
      api.resolveRequestWithN8n(replyingId, 'REQUEST_CORRECTION', composeData.body).catch(() => {});
    }

    setSentEmails(prev => [newSentEmail, ...prev]);
    setIsSending(false);
    setIsComposing(false);
    setSelectedEmail(newSentEmail);
    setActiveFolder('sent');
    
    setToastMessage('Respuesta enviada y trasladada a Enviados');
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  // Despacho de resolución manual a n8n
  const handleResolveAction = async (action: 'APPROVED' | 'DISAPPROVED' | 'REQUEST_CORRECTION') => {
    if (!selectedEmail) return;

    setIsResolving(true);
    setResolutionStatus(null);

    const notesToSend = hseNotes.trim() || (
      action === 'APPROVED' ? 'Justificación validada y aprobada por equipo de bienestar HSE.' :
      action === 'DISAPPROVED' ? 'Justificación denegada por no cumplir los criterios institucionales.' :
      'Se solicita aportar soporte documental adicional para tramitar la excusa.'
    );

    try {
      const result = await api.resolveRequestWithN8n(
        selectedEmail.id,
        action,
        notesToSend,
        {
          startDate,
          excuseType,
          reviewerName: 'Paola Admin (HSE)'
        }
      );

      const updatedReq = {
        ...result.request,
        hasHumanIntervention: true,
        hseDecision: action,
        isResponded: true,
      };

      // Actualizar en la lista local (sale automáticamente de Bandeja y entra a Enviados)
      setRequests(prev => prev.map(r => r.id === selectedEmail.id ? updatedReq : r));
      
      // Seleccionar el siguiente pendiente de la bandeja si quedan
      const remainingPending = inboxList.filter(r => r.id !== selectedEmail.id);
      if (remainingPending.length > 0) {
        handleSelectEmail(remainingPending[0]);
      } else {
        setSelectedEmail(null);
      }

      setToastMessage(`Caso ${action === 'APPROVED' ? 'Aprobado' : action === 'DISAPPROVED' ? 'Rechazado' : 'Notificado'} y movido a Enviados`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3500);
    } catch (err: any) {
      setResolutionStatus({
        type: 'error',
        message: 'Error al procesar la resolución',
        details: err.message
      });
    } finally {
      setIsResolving(false);
    }
  };
  const n8nConfig = getN8nConfig();

  return (
    <div className="h-[calc(100vh-6rem)] flex gap-4 overflow-hidden">
      
      {/* 1. SIDEBAR DE CARPETAS (Paneles Izquierdos) */}
      <div className="w-[240px] flex-shrink-0 flex flex-col gap-4">
        <button
          onClick={handleComposeNew}
          className="w-full bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-90 text-white rounded-[16px] py-4 px-4 flex items-center justify-center gap-2 font-bold shadow-[0_8px_20px_rgba(99,59,255,0.25)] transition-all cursor-pointer"
        >
          <FileEdit size={18} /> Redactar
        </button>

        <div className="bg-white border border-[#E2E8F0] rounded-[24px] p-3 flex-1 flex flex-col shadow-sm">
          <div className="space-y-1">
            <FolderButton 
              active={activeFolder === 'inbox'} 
              onClick={() => handleFolderChange('inbox')} 
              icon={<Inbox size={18} />} 
              label="Bandeja" 
              count={inboxList.length} 
            />
            <FolderButton 
              active={activeFolder === 'sent'} 
              onClick={() => handleFolderChange('sent')} 
              icon={<Send size={18} />} 
              label="Enviados" 
              count={sentList.length} 
            />
            <FolderButton 
              active={activeFolder === 'drafts'} 
              onClick={() => handleFolderChange('drafts')} 
              icon={<FileEdit size={18} />} 
              label="Borradores" 
              count={0} 
            />
          </div>

          {/* n8n Status Badge */}
          <div className="mt-auto pt-4 border-t border-[#E8EAF2]">
            <div className="p-3 bg-[#F8F9FE] border border-[#E8EAF2] rounded-[16px] text-xs">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-[#20B486] animate-pulse" />
                <span className="font-bold text-[#111827]">n8n Conectado</span>
              </div>
              <p className="text-[11px] text-[#7C8499] truncate font-mono">
                {n8nConfig.baseUrl}
              </p>
              <div className="mt-1 flex items-center gap-1 text-[10px] font-semibold text-[#5B3FF5]">
                <Zap size={11} /> {n8nConfig.useTestWebhook ? 'Modo Test' : 'Modo Producción'}
              </div>
            </div>
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
            const status = item.status;

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
                
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h4 className="text-[13px] font-semibold text-[#17203A] truncate">{subject}</h4>
                  {(item.category || status) && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 flex items-center gap-1 ${
                      (item.category === 'POSIBLEMENTE_VALIDO' || status === 'approved') ? 'bg-[#20B486]/10 text-[#20B486]' :
                      (item.category === 'POSIBLEMENTE_INVALIDO' || status === 'denied') ? 'bg-[#FF5C67]/10 text-[#FF5C67]' :
                      'bg-[#F5B83D]/10 text-[#F5B83D]'
                    }`}>
                      {(item.category === 'POSIBLEMENTE_VALIDO' || status === 'approved') ? 'Posiblemente Válido' :
                       (item.category === 'POSIBLEMENTE_INVALIDO' || status === 'denied') ? 'Posiblemente Inválido' :
                       'Revisión Manual'}
                      {typeof item.decision?.confidence === 'number' && item.decision.confidence > 0 && (
                        <span className="font-semibold opacity-90">({(item.decision.confidence * 100).toFixed(0)}%)</span>
                      )}
                    </span>
                  )}
                </div>

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
              className="absolute top-6 left-1/2 -translate-x-1/2 z-50 bg-[#11132C] text-white px-6 py-3 rounded-full font-bold shadow-xl flex items-center gap-2 border border-white/10"
            >
              <CheckCircle2 size={18} className="text-[#20B486]" /> {toastMessage}
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
                  className="bg-[#5B3FF5] hover:bg-[#4A2FE0] text-white px-8 py-2.5 rounded-[12px] font-bold flex items-center gap-2 transition-colors disabled:opacity-50 cursor-pointer"
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
          /* VISTA DE LECTURA Y RESOLUCIÓN */
          <div className="flex flex-col h-full overflow-hidden">
            {/* Cabecera del correo */}
            <div className="p-6 border-b border-[#E2E8F0] flex justify-between items-start bg-gray-50/30 shrink-0">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-[20px] font-bold text-[#111827]">
                    {selectedEmail.emailInfo?.subject || selectedEmail.subject}
                  </h2>
                  {(selectedEmail.category || selectedEmail.status) && (
                    <span className={`text-[11px] font-bold px-3 py-1 rounded-full flex items-center gap-1.5 ${
                      (selectedEmail.category === 'POSIBLEMENTE_VALIDO' || selectedEmail.status === 'approved') ? 'bg-[#20B486]/15 text-[#20B486]' :
                      (selectedEmail.category === 'POSIBLEMENTE_INVALIDO' || selectedEmail.status === 'denied') ? 'bg-[#FF5C67]/15 text-[#FF5C67]' :
                      'bg-[#F5B83D]/15 text-[#F5B83D]'
                    }`}>
                      {(selectedEmail.category === 'POSIBLEMENTE_VALIDO' || selectedEmail.status === 'approved') ? '● POSIBLEMENTE VÁLIDO' :
                       (selectedEmail.category === 'POSIBLEMENTE_INVALIDO' || selectedEmail.status === 'denied') ? '● POSIBLEMENTE INVÁLIDO' :
                       '● REVISIÓN MANUAL'}
                      {typeof selectedEmail.decision?.confidence === 'number' && selectedEmail.decision.confidence > 0 && (
                        <span className="font-mono bg-white/70 px-1.5 py-0.5 rounded text-[10px] text-gray-700">
                          {(selectedEmail.decision.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </span>
                  )}
                </div>

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
            
            {/* Contenido del correo */}
            <div className="flex-1 p-6 md:p-8 overflow-y-auto custom-scrollbar space-y-6">
              
              {/* Cuerpo del correo */}
              <div className="prose prose-sm max-w-none text-[#17203A] whitespace-pre-wrap leading-relaxed bg-[#FBFBFE] p-5 rounded-2xl border border-[#E8EAF2]">
                {selectedEmail.emailInfo?.body || selectedEmail.body}
              </div>

              {/* Adjuntos */}
              {selectedEmail.emailInfo?.attachments && selectedEmail.emailInfo.attachments.length > 0 && (
                <div className="pt-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#7C8499] mb-3">Adjuntos y Documentos</p>
                  <div className="flex flex-wrap gap-3">
                    {selectedEmail.emailInfo.attachments.map((att: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 border border-[#E2E8F0] p-2.5 pr-4 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer bg-white shadow-xs">
                        <div className="w-8 h-8 bg-red-100 text-red-500 rounded-lg flex items-center justify-center">
                          <Paperclip size={16} />
                        </div>
                        <span className="text-sm font-medium text-[#111827]">{att.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Caja de Análisis Asistido de IA HSE */}
              {selectedEmail.decision && (
                <div className="p-5 bg-gradient-to-br from-[#F2F0FF] to-[#FAF8FF] border border-[#5B3FF5]/25 rounded-2xl shadow-xs">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-[#5B3FF5] flex items-center justify-center text-white shadow-xs">
                        <User size={15} />
                      </div>
                      <span className="font-bold text-[14px] text-[#5B3FF5]">
                        {selectedEmail.decision.source === 'human' ? 'Resolución Humana Registrada' : 'Recomendación Asistida para la Team Leader (Strata Core)'}
                      </span>
                    </div>
                    {typeof selectedEmail.decision?.confidence === 'number' && selectedEmail.decision.confidence > 0 && (
                      <span className="text-[12px] font-bold text-[#5B3FF5] bg-[#5B3FF5]/10 px-3 py-1 rounded-full border border-[#5B3FF5]/20">
                        {(selectedEmail.decision.confidence * 100).toFixed(0)}% de Certidumbre
                      </span>
                    )}
                  </div>

                  {/* Indicador de categoría sugerida */}
                  <div className="mb-2.5 flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#7C8499] uppercase tracking-wider">Categoría Asistida:</span>
                    <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                      (selectedEmail.category === 'POSIBLEMENTE_VALIDO' || selectedEmail.status === 'approved') ? 'bg-[#20B486]/15 text-[#20B486]' :
                      (selectedEmail.category === 'POSIBLEMENTE_INVALIDO' || selectedEmail.status === 'denied') ? 'bg-[#FF5C67]/15 text-[#FF5C67]' :
                      'bg-[#F5B83D]/15 text-[#F5B83D]'
                    }`}>
                      {(selectedEmail.category === 'POSIBLEMENTE_VALIDO' || selectedEmail.status === 'approved') ? 'POSIBLEMENTE VÁLIDO' :
                       (selectedEmail.category === 'POSIBLEMENTE_INVALIDO' || selectedEmail.status === 'denied') ? 'POSIBLEMENTE INVÁLIDO' :
                       'REVISIÓN MANUAL'}
                    </span>
                  </div>

                  <p className="text-sm text-[#17203A] mb-2 leading-relaxed bg-white/70 p-3.5 rounded-xl border border-gray-100">
                    {selectedEmail.decision.reasoning}
                  </p>
                  {selectedEmail.decision.modifiedBy && (
                    <p className="text-xs text-[#7C8499] font-medium">
                      Modificado por: <strong className="text-[#111827]">{selectedEmail.decision.modifiedBy}</strong> · {new Date(selectedEmail.decision.modifiedAt).toLocaleTimeString('es-ES')}
                    </p>
                  )}
                </div>
              )}

              {/* ============================================================== */}
              {/* PANEL DE RESOLUCIÓN MANUAL Y DESPACHO A N8N                    */}
              {/* ============================================================== */}
              {/* ============================================================== */}
              {/* PANEL DE DETALLE: ENVIADOS (NOTIFICADO) vs BANDEJA (POR RESOLVER) */}
              {/* ============================================================== */}
              {(activeFolder === 'sent' || selectedEmail.hasHumanIntervention || selectedEmail.hseDecision) ? (
                <div className="border border-[#20B486]/30 bg-[#F4FDF9] rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center justify-between border-b border-[#20B486]/20 pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-[#20B486]/10 text-[#20B486] flex items-center justify-center">
                        <CheckCircle2 size={18} />
                      </div>
                      <div>
                        <h3 className="text-[15px] font-bold text-[#111827]">
                          Notificación Enviada al Coder
                        </h3>
                        <p className="text-xs text-[#7C8499]">
                          Esta justificación ya fue tramitada y su respuesta formal fue despachada.
                        </p>
                      </div>
                    </div>
                    <span className={`text-xs font-bold px-3 py-1 rounded-full ${
                      (selectedEmail.hseDecision === 'APPROVED' || selectedEmail.status === 'approved') ? 'bg-[#20B486]/15 text-[#20B486]' :
                      (selectedEmail.hseDecision === 'DISAPPROVED' || selectedEmail.status === 'denied') ? 'bg-[#FF5C67]/15 text-[#FF5C67]' :
                      'bg-[#F5B83D]/15 text-[#F5B83D]'
                    }`}>
                      {(selectedEmail.hseDecision === 'APPROVED' || selectedEmail.status === 'approved') ? 'Aprobado' :
                       (selectedEmail.hseDecision === 'DISAPPROVED' || selectedEmail.status === 'denied') ? 'Rechazado' :
                       (selectedEmail.hseDecision === 'REQUEST_CORRECTION') ? 'Soporte Solicitado' : 'Respondido'}
                    </span>
                  </div>

                  <div className="bg-white p-4 rounded-xl border border-emerald-100 shadow-xs">
                    <p className="text-xs font-bold text-[#7C8499] uppercase tracking-wider mb-1.5">
                      Respuesta / Justificación registrada por HSE:
                    </p>
                    <p className="text-sm text-[#17203A] leading-relaxed">
                      {selectedEmail.decision?.reasoning || selectedEmail.hseNotes || selectedEmail.body || 'Notificación formal enviada al estudiante.'}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-xs text-[#7C8499] pt-1">
                    <span>Revisor: <strong className="text-[#111827]">{selectedEmail.decision?.modifiedBy || 'Team Leader Paola'}</strong></span>
                    {selectedEmail.decision?.modifiedAt && (
                      <span>Fecha de envío: <strong>{new Date(selectedEmail.decision.modifiedAt).toLocaleString('es-ES')}</strong></span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="border-2 border-[#5B3FF5]/20 bg-white rounded-2xl p-6 shadow-sm space-y-4">
                  <div className="flex items-center justify-between border-b border-[#E8EAF2] pb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-[#5B3FF5]/10 text-[#5B3FF5] flex items-center justify-center">
                        <Zap size={18} />
                      </div>
                      <div>
                        <h3 className="text-[15px] font-bold text-[#111827]">
                          Resolución Manual HSE & Despacho a n8n
                        </h3>
                        <p className="text-xs text-[#7C8499]">
                          Al confirmar la decisión, el mensaje se responderá formalmente y se moverá a <strong>Enviados</strong>.
                        </p>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-[#7C8499] hidden sm:block">
                      POST {n8nConfig.dispatchWebhookPath}
                    </span>
                  </div>

                  {/* Feedback de resultado */}
                  {resolutionStatus && (
                    <div className={`p-4 rounded-xl text-sm border flex items-start gap-3 ${
                      resolutionStatus.type === 'success' ? 'bg-[#20B486]/10 border-[#20B486]/30 text-[#136c50]' :
                      resolutionStatus.type === 'warning' ? 'bg-[#F5B83D]/10 border-[#F5B83D]/30 text-[#855e09]' :
                      'bg-[#FF5C67]/10 border-[#FF5C67]/30 text-[#9c242c]'
                    }`}>
                      {resolutionStatus.type === 'success' ? <CheckCircle2 size={18} className="shrink-0 mt-0.5" /> :
                       resolutionStatus.type === 'warning' ? <AlertTriangle size={18} className="shrink-0 mt-0.5" /> :
                       <AlertCircle size={18} className="shrink-0 mt-0.5" />}
                      <div>
                        <p className="font-bold">{resolutionStatus.message}</p>
                        {resolutionStatus.details && (
                          <p className="text-xs mt-1 opacity-90">{resolutionStatus.details}</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Formulario de corrección */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#7C8499] mb-1.5 flex items-center gap-1.5">
                        <Calendar size={13} /> Fecha Afectada
                      </label>
                      <input 
                        type="date"
                        value={startDate}
                        onChange={e => setStartDate(e.target.value)}
                        className="w-full bg-[#F8F9FD] border border-[#E8EAF2] rounded-xl px-3.5 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#5B3FF5]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-[#7C8499] mb-1.5 flex items-center gap-1.5">
                        <ShieldCheck size={13} /> Tipo de Novedad
                      </label>
                      <select
                        value={excuseType}
                        onChange={e => setExcuseType(e.target.value)}
                        className="w-full bg-[#F8F9FD] border border-[#E8EAF2] rounded-xl px-3.5 py-2 text-sm text-[#111827] focus:outline-none focus:border-[#5B3FF5]"
                      >
                        <option value="inasistencia_medica">Inasistencia Médica / EPS</option>
                        <option value="calamidad">Calamidad Familiar / Doméstica</option>
                        <option value="tramite_legal">Trámite Legal / Cita Oficial</option>
                        <option value="fuerza_mayor">Fuerza Mayor / Desplazamiento</option>
                        <option value="falla_tecnica">Falla Técnica / Falta de Conectividad</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[#7C8499] mb-1.5 flex items-center gap-1.5">
                      <MessageSquare size={13} /> Observaciones / Justificación de la Decisión (se incluirá en el correo n8n)
                    </label>
                    <textarea 
                      rows={3}
                      value={hseNotes}
                      onChange={e => setHseNotes(e.target.value)}
                      placeholder="Escribe las notas de aprobación, rechazo o requerimientos para el coder..."
                      className="w-full bg-[#F8F9FD] border border-[#E8EAF2] rounded-xl p-3 text-sm text-[#111827] focus:outline-none focus:border-[#5B3FF5] resize-none leading-relaxed"
                    />
                  </div>

                  {/* Botones de Acción */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <span className="text-xs text-[#7C8499]">
                      Revisor: <strong>Paola Admin (HSE)</strong>
                    </span>

                    <div className="flex items-center gap-2">
                      {/* Botón Rechazar */}
                      <button
                        type="button"
                        disabled={isResolving}
                        onClick={() => handleResolveAction('DISAPPROVED')}
                        className="bg-white hover:bg-red-50 text-[#FF5C67] border border-[#FF5C67]/30 hover:border-[#FF5C67] px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                      >
                        <XCircle size={15} /> Rechazar Caso
                      </button>

                      {/* Botón Solicitar Corrección */}
                      <button
                        type="button"
                        disabled={isResolving}
                        onClick={() => handleResolveAction('REQUEST_CORRECTION')}
                        className="bg-white hover:bg-amber-50 text-[#F5B83D] border border-[#F5B83D]/30 hover:border-[#F5B83D] px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                      >
                        <AlertTriangle size={15} /> Pedir Soporte
                      </button>

                      {/* Botón Aprobar */}
                      <button
                        type="button"
                        disabled={isResolving}
                        onClick={() => handleResolveAction('APPROVED')}
                        className="bg-[#20B486] hover:bg-[#199d74] text-white shadow-md shadow-[#20B486]/25 px-5 py-2.5 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                      >
                        {isResolving ? (
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                          <><CheckCircle2 size={15} /> Aprobar Excusa</>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer de opciones */}
            <div className="p-4 border-t border-[#E2E8F0] bg-gray-50/50 flex items-center justify-between shrink-0">
              <button 
                onClick={handleReply}
                className="bg-white border border-[#E2E8F0] hover:bg-gray-50 text-[#17203A] px-5 py-2 rounded-[12px] font-bold text-sm flex items-center gap-2 transition-colors shadow-xs cursor-pointer"
              >
                <Reply size={16} /> Redactar respuesta
              </button>

              <div className="flex items-center gap-2 text-xs text-[#7C8499]">
                <Zap size={14} className="text-[#5B3FF5]" />
                <span>Workflow destino:</span>
                <span className="font-mono text-[#111827]">{n8nConfig.baseUrl}</span>
              </div>
            </div>
          </div>
        ) : (
          /* VISTA VACIA */
          <div className="flex-1 flex flex-col items-center justify-center text-[#A3AAC2] p-8 text-center">
            <Mail size={64} className="mb-4 opacity-20" />
            <h3 className="text-xl font-bold text-[#111827] mb-2">Ningún mensaje seleccionado</h3>
            <p className="max-w-[300px]">Selecciona un correo de la lista a la izquierda para auditarlo, validarlo y despachar la resolución al workflow de n8n.</p>
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
      className={`w-full flex items-center justify-between p-3 rounded-[12px] transition-colors cursor-pointer ${
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
