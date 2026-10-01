import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, Send, FileEdit, Trash, Reply, Inbox, Paperclip, User, 
  CheckCircle2, XCircle, AlertCircle, Zap,
  Calendar, ShieldCheck, MessageSquare, AlertTriangle, RotateCw, Search,
  ArrowLeft, Download, FileText, Image as ImageIcon, X
} from 'lucide-react';
import clsx from 'clsx';
import { api } from '../services/api';
import { matchesNormalized } from '../utils/textUtils';

export default function Requests() {
  const [activeFolder, setActiveFolder] = useState<'inbox' | 'sent' | 'drafts'>('inbox');
  const [requests, setRequests] = useState<any[]>([]);
  const [sentEmails, setSentEmails] = useState<any[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<any | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showMobileDetail, setShowMobileDetail] = useState(false);
  
  // Preview Modal State for Attachments (Images and Documents)
  const [previewModalAttachment, setPreviewModalAttachment] = useState<{
    name: string;
    url: string;
    mime_type?: string;
  } | null>(null);

  const isImageAttachment = (att: { name: string; url: string; mime_type?: string }) => {
    const mime = (att.mime_type || '').toLowerCase();
    if (mime.startsWith('image/')) return true;
    if (att.url && att.url.startsWith('data:image/')) return true;
    const ext = (att.name || '').toLowerCase();
    return ext.endsWith('.png') || ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.gif') || ext.endsWith('.webp') || ext.endsWith('.svg');
  };

  const handleDownloadAttachment = (e: React.MouseEvent, att: { name: string; url: string }) => {
    e.stopPropagation();
    e.preventDefault();
    if (!att.url || att.url === '#') return;
    try {
      const link = document.createElement('a');
      link.href = att.url;
      link.download = att.name || 'documento_soporte';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error al descargar archivo:', err);
    }
  };

  const handleOpenPreview = (e: React.MouseEvent, att: { name: string; url: string; mime_type?: string }) => {
    e.stopPropagation();
    e.preventDefault();
    setPreviewModalAttachment(att);
  };

  // Composing state
  const [isComposing, setIsComposing] = useState(false);
  const [composeData, setComposeData] = useState({ to: '', subject: '', body: '' });
  const [isSending, setIsSending] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('Mensaje enviado');

  // Manual Resolution State
  const [hseNotes, setHseNotes] = useState('');
  const [excuseType, setExcuseType] = useState('inasistencia_medica');
  const [startDate, setStartDate] = useState('');
  const [isResolving, setIsResolving] = useState(false);
  const [resolutionStatus, setResolutionStatus] = useState<{
    type: 'success' | 'warning' | 'error';
    message: string;
    details?: string;
  } | null>(null);

  const inboxList = requests.filter((r: any) => !r.hasHumanIntervention && !r.hseDecision && !r.isResponded);
  const resolvedRequests = requests.filter((r: any) => r.hasHumanIntervention || r.hseDecision || r.isResponded);
  const sentList = [...resolvedRequests, ...sentEmails];
  const activeList = activeFolder === 'inbox' ? inboxList : activeFolder === 'sent' ? sentList : [];

  const filteredActiveList = activeList.filter((item: any) => {
    const q = searchQuery.trim();
    if (!q) return true;
    const subject = item.emailInfo?.subject || item.subject || '';
    const sender = item.emailInfo?.senderName || item.to || '';
    const body = item.emailInfo?.body || item.body || '';
    return (
      matchesNormalized(subject, q) ||
      matchesNormalized(sender, q) ||
      matchesNormalized(body, q)
    );
  });

  const fetchRequests = async (showSpinner = false) => {
    if (showSpinner) setIsRefreshing(true);
    try {
      const data = await api.getRequests();
      setRequests(data);
      setSelectedEmail((prev: any) => {
        if (!prev) {
          const pending = data.filter((r: any) => !r.hasHumanIntervention && !r.hseDecision && !r.isResponded);
          return pending.length > 0 ? pending[0] : (data.length > 0 ? data[0] : null);
        }
        const updated = data.find((r: any) => r.id === prev.id);
        return updated || prev;
      });
    } catch (e) {
      console.warn('Error al sincronizar solicitudes:', e);
    } finally {
      if (showSpinner) setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(() => {
      fetchRequests(false);
    }, 3500);

    const handleSync = () => {
      fetchRequests(false);
    };

    window.addEventListener('hse_justification_created', handleSync);
    window.addEventListener('hse_justifications_updated', handleSync);
    window.addEventListener('storage', handleSync);

    return () => {
      clearInterval(interval);
      window.removeEventListener('hse_justification_created', handleSync);
      window.removeEventListener('hse_justifications_updated', handleSync);
      window.removeEventListener('storage', handleSync);
    };
  }, []);

  const handleFolderChange = (folder: 'inbox' | 'sent' | 'drafts') => {
    setActiveFolder(folder);
    setIsComposing(false);
    setResolutionStatus(null);
    setShowMobileDetail(false);
    const targetList = folder === 'inbox' ? inboxList : folder === 'sent' ? sentList : [];
    if (targetList.length > 0) {
      handleSelectEmail(targetList[0]);
      setShowMobileDetail(false); // Mantener en lista en móvil al cambiar carpeta
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
      api.resolveJustification(replyingId, {
        action: 'REQUEST_MORE_INFO',
        notes: composeData.body,
        reviewer_name: 'Paola Admin (HSE)'
      }).catch(() => {});
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

  // Despacho de resolución manual al backend nativo
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
      const result = await api.resolveJustification(
        selectedEmail.id,
        {
          action,
          notes: notesToSend,
          reviewer_name: 'Paola Admin (HSE)',
          override_start_date: startDate || undefined,
          override_excuse_type: excuseType,
          dispatch_notification: true
        }
      );

      const updatedReq = {
        ...selectedEmail,
        ...result.updatedRequest,
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

      const actionLabel = action === 'APPROVED' ? 'Aprobado' : action === 'DISAPPROVED' ? 'Rechazado' : 'Notificado';
      setToastMessage(`Caso ${actionLabel} exitosamente y registrado en backend`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3500);

      setResolutionStatus({
        type: 'success',
        message: `Caso ${actionLabel.toLowerCase()} formalmente por el equipo HSE`,
        details: 'Decisión persistida en base de datos y correo formal notificado al coder.'
      });
    } catch (err: any) {
      setResolutionStatus({
        type: 'error',
        message: 'Error al procesar la resolución en el servidor',
        details: err?.message || 'Fallo de conexión'
      });
      setToastMessage('Error al procesar la resolución');
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3500);
    } finally {
      setIsResolving(false);
    }
  };

  const handleDownloadReport = () => {
    const list = [...inboxList, ...sentList];
    const headers = ['ID Radicado', 'Remitente', 'Asunto', 'Fecha', 'Estado'];
    const rows = list.map((item) => [
      `"${item.id || ''}"`,
      `"${item.from_address || item.to_address || ''}"`,
      `"${(item.subject || '').replace(/"/g, '""')}"`,
      `"${item.received_at || item.sent_at || ''}"`,
      `"${item.status || 'PROCESADO'}"`,
    ]);
    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `reporte_solicitudes_hse_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="h-[calc(100vh-5.5rem)] lg:h-[calc(100vh-6rem)] flex flex-col gap-3 overflow-hidden">
      {/* Top Header con Título y Botón Descargar Reporte en la esquina superior derecha */}
      <div className="flex items-center justify-between gap-3 shrink-0">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#111827]">Bandeja de Solicitudes HSE</h1>
          <p className="text-xs text-[#7C8499]">Gestión de justificaciones, incapacidades y radicados de bienestar.</p>
        </div>
        <button
          type="button"
          onClick={handleDownloadReport}
          className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-gray-50 border border-[#E2E8F0] rounded-xl text-xs sm:text-sm font-semibold text-[#111827] shadow-2xs transition-all cursor-pointer hover:border-[#5B3FF5]"
          title="Descargar reporte consolidado en CSV"
        >
          <Download size={14} className="text-[#5B3FF5]" />
          <span>Descargar reporte</span>
        </button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-3 sm:gap-4 overflow-hidden min-h-0">
      
      {/* Selector móvil de carpetas (solo visible en < 1024px) */}
      <div className="lg:hidden flex items-center justify-between gap-2 overflow-x-auto pb-1 shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          <button
            type="button"
            onClick={() => handleFolderChange('inbox')}
            className={clsx(
              "px-3 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 cursor-pointer",
              activeFolder === 'inbox' ? "bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/30" : "bg-white text-[#7C8499] border border-[#E2E8F0]"
            )}
          >
            <Inbox size={14} /> Bandeja ({inboxList.length})
          </button>
          <button
            type="button"
            onClick={() => handleFolderChange('sent')}
            className={clsx(
              "px-3 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 cursor-pointer",
              activeFolder === 'sent' ? "bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/30" : "bg-white text-[#7C8499] border border-[#E2E8F0]"
            )}
          >
            <Send size={14} /> Enviados ({sentList.length})
          </button>
          <button
            type="button"
            onClick={() => handleFolderChange('drafts')}
            className={clsx(
              "px-3 py-1.5 rounded-full text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 cursor-pointer",
              activeFolder === 'drafts' ? "bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/30" : "bg-white text-[#7C8499] border border-[#E2E8F0]"
            )}
          >
            <FileEdit size={14} /> Borradores
          </button>
        </div>
        <button
          type="button"
          onClick={() => { handleComposeNew(); setShowMobileDetail(true); }}
          className="bg-gradient-to-r from-[#5636F5] to-[#633BFF] text-white px-3 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5 shrink-0 shadow-sm cursor-pointer"
        >
          <FileEdit size={13} /> Redactar
        </button>
      </div>

      {/* 1. SIDEBAR DE CARPETAS (Paneles Izquierdos en Desktop) */}
      <div className="hidden lg:flex w-[240px] flex-shrink-0 flex-col gap-4">
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

          {/* Backend Status Badge */}
          <div className="mt-auto pt-4 border-t border-[#E8EAF2]">
            <div className="p-3 bg-[#F8F9FE] border border-[#E8EAF2] rounded-[16px] text-xs">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-[#20B486] animate-pulse" />
                <span className="font-bold text-[#111827]">Backend REST Nativo</span>
              </div>
              <p className="text-[11px] text-[#7C8499] truncate font-mono">
                /api/v1/justifications
              </p>
              <div className="mt-1 flex items-center gap-1 text-[10px] font-semibold text-[#5B3FF5]">
                <Zap size={11} /> Conexión Directa HSE
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. LISTA DE CORREOS (Panel Central) */}
      <div className={clsx(
        "w-full lg:w-[380px] flex-shrink-0 bg-white border border-[#E2E8F0] rounded-[24px] shadow-sm flex flex-col overflow-hidden",
        showMobileDetail ? "hidden lg:flex" : "flex flex-1 lg:flex-initial"
      )}>
        <div className="p-4 border-b border-[#E2E8F0] bg-gray-50/50 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[16px] sm:text-[18px] font-bold text-[#111827] capitalize">
                {activeFolder === 'inbox' ? 'Bandeja de Entrada' : activeFolder === 'sent' ? 'Enviados' : 'Borradores'}
              </h2>
              <p className="text-xs text-[#7C8499]">{filteredActiveList.length} correos</p>
            </div>
            <button
              onClick={() => fetchRequests(true)}
              title="Sincronizar correos ahora"
              className="p-2 text-[#7C8499] hover:text-[#5B3FF5] hover:bg-white rounded-full transition-colors cursor-pointer border border-transparent hover:border-[#E2E8F0]"
            >
              <RotateCw size={16} className={isRefreshing ? 'animate-spin text-[#5B3FF5]' : ''} />
            </button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7C8499]" size={14} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por asunto, remitente o texto..."
              className="pl-9 pr-3 py-1.5 w-full bg-white border border-[#E2E8F0] rounded-xl text-xs focus:outline-none focus:border-[#5B3FF5] transition-all text-[#111827] placeholder:text-[#A3AAC2]"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {filteredActiveList.map((item: any) => {
            const isSelected = selectedEmail?.id === item.id && !isComposing;
            const subject = item.emailInfo?.subject || item.subject;
            const sender = item.emailInfo?.senderName || item.to;
            const date = new Date(item.emailInfo?.date || item.date).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
            const snippet = item.emailInfo?.body || item.body;
            const status = item.status;

            return (
              <div 
                key={item.id} 
                onClick={() => {
                  handleSelectEmail(item);
                  setShowMobileDetail(true);
                }}
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
            <div className="h-full flex flex-col items-center justify-center p-6 text-center text-[#7C8499]">
              <Inbox size={42} className="stroke-[1.5] text-[#A3AAC2] mb-3" />
              <p className="text-sm font-semibold text-[#111827]">
                {activeFolder === 'inbox' ? 'Bandeja de entrada al día' : 'No hay correos en esta sección'}
              </p>
              <p className="text-xs text-[#7C8499] mt-1 max-w-[220px]">
                {activeFolder === 'inbox' 
                  ? 'No hay justificaciones pendientes. Los correos resueltos se encuentran en "Enviados".' 
                  : 'Los mensajes aparecerán aquí cuando sean procesados.'}
              </p>
              {activeFolder === 'inbox' && sentList.length > 0 && (
                <button
                  onClick={() => handleFolderChange('sent')}
                  className="mt-4 text-xs font-bold text-[#5B3FF5] hover:underline cursor-pointer"
                >
                  Ver {sentList.length} correos en Enviados →
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 3. VISOR / EDITOR (Panel Derecho) */}
      <div className={clsx(
        "flex-1 bg-white border border-[#E2E8F0] rounded-[24px] shadow-sm flex flex-col overflow-hidden relative",
        !showMobileDetail ? "hidden lg:flex" : "flex"
      )}>
        
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
            <div className="p-4 sm:p-5 border-b border-[#E2E8F0] flex justify-between items-center bg-gray-50/50">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowMobileDetail(false)}
                  className="lg:hidden p-1.5 rounded-lg text-[#7C8499] hover:bg-white hover:text-[#111827] transition-colors cursor-pointer"
                  aria-label="Volver a la lista"
                >
                  <ArrowLeft size={18} />
                </button>
                <h2 className="text-[16px] sm:text-[18px] font-bold text-[#111827]">Nuevo Mensaje</h2>
              </div>
              <button 
                onClick={() => {
                  setIsComposing(false);
                  setShowMobileDetail(false);
                }} 
                className="text-[#A3AAC2] hover:text-red-500 transition-colors p-1"
                aria-label="Cerrar redacción"
              >
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
            <div className="p-4 sm:p-6 border-b border-[#E2E8F0] flex flex-col sm:flex-row justify-between items-start gap-3 bg-gray-50/30 shrink-0">
              <div className="w-full sm:w-auto">
                <div className="flex items-center gap-2 mb-2">
                  <button
                    type="button"
                    onClick={() => setShowMobileDetail(false)}
                    className="lg:hidden p-1.5 -ml-1 rounded-lg text-[#7C8499] hover:bg-white hover:text-[#111827] transition-colors shrink-0 cursor-pointer"
                    aria-label="Volver a la lista"
                  >
                    <ArrowLeft size={18} />
                  </button>
                  <h2 className="text-[17px] sm:text-[20px] font-bold text-[#111827] line-clamp-1 sm:line-clamp-none">
                    {selectedEmail.emailInfo?.subject || selectedEmail.subject}
                  </h2>
                </div>

                <div className="flex flex-wrap items-center gap-2 mb-3">
                  {(selectedEmail.category || selectedEmail.status) && (
                    <span className={`text-[10px] sm:text-[11px] font-bold px-2.5 sm:px-3 py-1 rounded-full flex items-center gap-1.5 ${
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
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gradient-to-tr from-[#5B3FF5] to-blue-400 flex items-center justify-center text-white font-bold shrink-0">
                    {(selectedEmail.emailInfo?.senderName || selectedEmail.to || 'A')[0]}
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-[13px] sm:text-[14px] text-[#111827] truncate">
                      {selectedEmail.emailInfo?.senderName || (activeFolder === 'sent' ? 'Yo (Admin)' : selectedEmail.to)}
                    </p>
                    <p className="text-[11px] sm:text-[12px] text-[#7C8499] truncate">
                      {activeFolder === 'sent' ? `Para: ${selectedEmail.to}` : `<${selectedEmail.emailInfo?.senderEmail}>`}
                    </p>
                  </div>
                </div>
              </div>
              <p className="text-xs sm:text-sm text-[#A3AAC2] self-end sm:self-auto">
                {new Date(selectedEmail.emailInfo?.date || selectedEmail.date).toLocaleString('es-ES')}
              </p>
            </div>
            
            {/* Contenido del correo */}
            <div className="flex-1 p-6 md:p-8 overflow-y-auto custom-scrollbar space-y-6">
              
              {/* Cuerpo del correo */}
              <div className="prose prose-sm max-w-none text-[#17203A] whitespace-pre-wrap leading-relaxed bg-[#FBFBFE] p-5 rounded-2xl border border-[#E8EAF2]">
                {selectedEmail.emailInfo?.body || selectedEmail.body}
              </div>

              {/* Adjuntos y Evidencias */}
              {((selectedEmail.emailInfo?.attachments && selectedEmail.emailInfo.attachments.length > 0) || (selectedEmail.emailInfo?.images && selectedEmail.emailInfo.images.length > 0)) && (
                <div className="pt-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#7C8499] mb-3">Adjuntos y Documentos Probatorios</p>
                  <div className="flex flex-wrap gap-3">
                    {[
                      ...(selectedEmail.emailInfo?.attachments || []),
                      ...((selectedEmail.emailInfo?.images || []).map((imgUrl: string, idx: number) => ({
                        name: `soporte_evidencia_${idx + 1}.png`,
                        url: imgUrl,
                        mime_type: 'image/png'
                      })))
                    ].map((att: any, i: number) => {
                      const hasValidUrl = Boolean(att.url && att.url !== '#');
                      const isImg = isImageAttachment(att);
                      return (
                        <div
                          key={i}
                          onClick={(e) => hasValidUrl && handleOpenPreview(e, att)}
                          title={hasValidUrl ? 'Click para previsualizar documento o imagen' : 'Documento adjunto'}
                          className={`flex items-center justify-between gap-3 border border-[#E2E8F0] p-2.5 px-3.5 rounded-xl transition-all bg-white shadow-xs ${
                            hasValidUrl
                              ? 'hover:border-[#5B3FF5] hover:bg-[#F2F0FF]/30 hover:shadow-sm cursor-pointer group'
                              : 'cursor-default'
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform shrink-0 ${
                              isImg ? 'bg-[#5B3FF5]/10 text-[#5B3FF5]' : 'bg-red-100 text-red-500'
                            }`}>
                              {isImg ? <ImageIcon size={16} /> : <FileText size={16} />}
                            </div>
                            <div className="flex flex-col min-w-0">
                              <span className="text-sm font-medium text-[#111827] group-hover:text-[#5B3FF5] transition-colors truncate max-w-[200px]">
                                {att.name}
                              </span>
                              {hasValidUrl && (
                                <span className="text-[10px] text-[#5B3FF5] font-bold">Ver evidencia ↗</span>
                              )}
                            </div>
                          </div>
                          {hasValidUrl && (
                            <button
                              type="button"
                              onClick={(e) => handleDownloadAttachment(e, att)}
                              title="Descargar archivo a tu dispositivo"
                              className="p-1.5 text-[#7C8499] hover:text-[#5B3FF5] hover:bg-[#5B3FF5]/10 rounded-lg transition-colors ml-2 shrink-0 cursor-pointer"
                            >
                              <Download size={15} />
                            </button>
                          )}
                        </div>
                      );
                    })}
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
              {/* PANEL DE RESOLUCIÓN MANUAL Y DESPACHO A BACKEND NATIVO        */}
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
                          Resolución Oficial HSE (Backend API Nativo)
                        </h3>
                        <p className="text-xs text-[#7C8499]">
                          Al confirmar la decisión, el mensaje se responderá formalmente y se moverá a <strong>Enviados</strong>.
                        </p>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-[#7C8499] hidden sm:block">
                      POST /api/v1/justifications/resolve
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
                      <MessageSquare size={13} /> Observaciones / Justificación de la Decisión (se incluirá en la notificación oficial)
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
                <span>Servicio destino:</span>
                <span className="font-mono text-[#111827]">API REST Nativa</span>
              </div>
            </div>
          </div>
        ) : (
          /* VISTA VACIA */
          <div className="flex-1 flex flex-col items-center justify-center text-[#A3AAC2] p-8 text-center">
            <Mail size={64} className="mb-4 opacity-20" />
            <h3 className="text-xl font-bold text-[#111827] mb-2">Ningún mensaje seleccionado</h3>
            <p className="max-w-[300px]">Selecciona un correo de la lista a la izquierda para auditarlo, validarlo y registrar la resolución oficial.</p>
          </div>
        )}
      </div>

      {/* Modal de Previsualización y Descarga de Archivos / Imágenes */}
      <AnimatePresence>
        {previewModalAttachment && (
          <div 
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
            onClick={() => setPreviewModalAttachment(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
            >
              {/* Header Modal */}
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/90">
                <div className="flex items-center gap-3 min-w-0">
                  <div className={`p-2 rounded-xl ${
                    isImageAttachment(previewModalAttachment) 
                      ? 'bg-[#5B3FF5]/10 text-[#5B3FF5]' 
                      : 'bg-red-50 text-red-500'
                  }`}>
                    {isImageAttachment(previewModalAttachment) ? <ImageIcon size={20} /> : <FileText size={20} />}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-bold text-[#111827] text-sm md:text-base truncate max-w-[320px] md:max-w-md">
                      {previewModalAttachment.name}
                    </h3>
                    <p className="text-xs text-[#7C8499]">
                      {isImageAttachment(previewModalAttachment) ? 'Soporte Fotográfico / Imagen' : 'Documento Probatorio / PDF'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={(e) => handleDownloadAttachment(e, previewModalAttachment)}
                    className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-[#5B3FF5] hover:bg-[#492fe0] rounded-xl transition-all shadow-xs cursor-pointer"
                    title="Descargar archivo a tu dispositivo"
                  >
                    <Download size={14} />
                    <span>Descargar</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewModalAttachment(null)}
                    className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition-colors cursor-pointer"
                    title="Cerrar visor"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* Visor Content */}
              <div className="p-4 md:p-6 flex-1 overflow-auto flex items-center justify-center bg-slate-100/60 min-h-[350px]">
                {isImageAttachment(previewModalAttachment) ? (
                  <div className="flex flex-col items-center justify-center max-w-full">
                    <img
                      src={previewModalAttachment.url}
                      alt={previewModalAttachment.name}
                      className="max-h-[68vh] max-w-full object-contain rounded-xl shadow-md border border-slate-200 bg-white"
                    />
                  </div>
                ) : (
                  <div className="w-full h-full flex flex-col items-center">
                    <iframe
                      src={previewModalAttachment.url}
                      title={previewModalAttachment.name}
                      className="w-full h-[68vh] rounded-xl border border-slate-200 bg-white shadow-sm"
                    />
                  </div>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      
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
