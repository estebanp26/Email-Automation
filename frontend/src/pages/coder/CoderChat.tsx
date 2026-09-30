import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, 
  Send, 
  Search, 
  CheckCircle2, 
  ShieldCheck, 
  ArrowLeft, 
  Mail, 
  Check 
} from 'lucide-react';
import { 
  getMessagesForCoder, 
  markMessageRead, 
  addCoderReply, 
  type HseMessage 
} from '../../services/hseMessages';
import { getCoderSession } from '../../utils/coderSession';
import { useAuth } from '../../context/AuthContext';
import { CoderProfileMenu } from '../../components/coder/CoderProfileMenu';

export default function CoderChat() {
  const { user } = useAuth();
  const session = useMemo(() => {
    if (user && user.role === 'CODER') {
      return {
        name: user.name,
        cedula: user.cedula || '',
        email: user.email,
        route: user.route || 'Desarrollo de Software',
      };
    }
    return getCoderSession();
  }, [user]);

  const [messages, setMessages] = useState<HseMessage[]>([]);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<'ALL' | 'ROUTE' | 'CODER' | 'UNREAD'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [replyText, setReplyText] = useState('');
  const [showMobileDetail, setShowMobileDetail] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const refreshMessages = () => {
    const list = getMessagesForCoder({
      email: session.email,
      route: session.route,
      cedula: session.cedula,
      name: session.name
    });
    setMessages(list);

    if (list.length > 0 && (!selectedMessageId || !list.some(m => m.id === selectedMessageId))) {
      setSelectedMessageId(list[0].id);
    }
  };

  useEffect(() => {
    refreshMessages();

    const handleUpdate = () => refreshMessages();
    window.addEventListener('hse_messages_updated', handleUpdate);
    return () => window.removeEventListener('hse_messages_updated', handleUpdate);
  }, [session]);

  const selectedMessage = useMemo(() => {
    return messages.find(m => m.id === selectedMessageId) || null;
  }, [messages, selectedMessageId]);

  const handleSelectMessage = (msg: HseMessage) => {
    setSelectedMessageId(msg.id);
    setShowMobileDetail(true);
    if (!msg.read) {
      markMessageRead(msg.id);
      setMessages(prev => prev.map(m => m.id === msg.id ? { ...m, read: true } : m));
    }
  };

  const filteredMessages = useMemo(() => {
    return messages.filter(msg => {
      if (filterType === 'ROUTE' && msg.recipientType !== 'ROUTE' && msg.recipientType !== 'ALL') return false;
      if (filterType === 'CODER' && msg.recipientType !== 'CODER') return false;
      if (filterType === 'UNREAD' && msg.read) return false;

      const q = searchQuery.toLowerCase().trim();
      if (!q) return true;
      return (
        msg.subject.toLowerCase().includes(q) ||
        msg.body.toLowerCase().includes(q) ||
        msg.sender.toLowerCase().includes(q)
      );
    });
  }, [messages, filterType, searchQuery]);

  const handleSendReply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || !selectedMessage) return;

    addCoderReply(selectedMessage.id, replyText, session.name || 'Coder Riwi');
    setReplyText('');
    showToast('Respuesta despachada al equipo HSE');
    refreshMessages();
  };

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col gap-4 relative">
      
      {/* Toast Flotante */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-8 right-8 z-50 bg-[#11132C] text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 border border-white/10 text-sm font-semibold"
          >
            <CheckCircle2 size={18} className="text-[#20B486]" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* TOP HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 shrink-0">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#111827] flex items-center gap-2">
            <MessageSquare className="text-[#5B3FF5]" size={24} />
            Bandeja de Mensajes & Chat HSE
          </h1>
          <p className="text-xs text-[#7C8499] mt-0.5">
            Comunicaciones oficiales de bienestar, circulares de ruta y seguimiento para {session.name}.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start sm:self-auto">
          <div className="flex items-center gap-2 text-xs bg-white px-3.5 py-1.5 rounded-full border border-[#E2E8F0] text-[#7C8499] font-medium shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-[#20B486] animate-pulse" />
            <span className="hidden sm:inline">Canal Directo HSE Barranquilla</span>
            <span className="sm:hidden">HSE Barranquilla</span>
          </div>
          <CoderProfileMenu />
        </div>
      </div>

      {/* MAIN CONTAINER: 2 PANELES */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 overflow-hidden min-h-0">
        
        {/* PANEL IZQUIERDO: LISTA DE MENSAJES HSE */}
        <div className={`w-full lg:w-[380px] bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm flex flex-col overflow-hidden shrink-0 ${
          showMobileDetail ? 'hidden lg:flex' : 'flex'
        }`}>
          
          <div className="p-4 border-b border-[#E2E8F0] bg-gray-50/50 space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7C8499]" size={15} />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Buscar comunicado o asunto..."
                className="w-full pl-9 pr-3 py-2 bg-white border border-[#E2E8F0] rounded-xl text-xs font-medium focus:border-[#5B3FF5] focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              <button
                type="button"
                onClick={() => setFilterType('ALL')}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap ${
                  filterType === 'ALL'
                    ? 'bg-[#5B3FF5] text-white shadow-2xs'
                    : 'bg-white text-[#7C8499] border border-[#E2E8F0] hover:text-[#111827]'
                }`}
              >
                Todos ({messages.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterType('ROUTE')}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap ${
                  filterType === 'ROUTE'
                    ? 'bg-[#5B3FF5] text-white shadow-2xs'
                    : 'bg-white text-[#7C8499] border border-[#E2E8F0] hover:text-[#111827]'
                }`}
              >
                Ruta
              </button>
              <button
                type="button"
                onClick={() => setFilterType('CODER')}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap ${
                  filterType === 'CODER'
                    ? 'bg-[#5B3FF5] text-white shadow-2xs'
                    : 'bg-white text-[#7C8499] border border-[#E2E8F0] hover:text-[#111827]'
                }`}
              >
                Personalizados
              </button>
              <button
                type="button"
                onClick={() => setFilterType('UNREAD')}
                className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer whitespace-nowrap ${
                  filterType === 'UNREAD'
                    ? 'bg-[#5B3FF5] text-white shadow-2xs'
                    : 'bg-white text-[#7C8499] border border-[#E2E8F0] hover:text-[#111827]'
                }`}
              >
                No leídos
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-[#E2E8F0]">
            {filteredMessages.length === 0 ? (
              <div className="p-8 text-center text-[#7C8499] text-xs">
                <Mail size={32} className="mx-auto mb-2 opacity-30 text-[#5B3FF5]" />
                <p className="font-semibold text-[#111827]">Sin mensajes en esta bandeja</p>
                <p className="mt-1">Aquí recibirás los comunicados emitidos por el equipo HSE.</p>
              </div>
            ) : (
              filteredMessages.map(item => {
                const isSelected = selectedMessageId === item.id;
                const isPersonal = item.recipientType === 'CODER';
                const isUrgent = item.priority === 'URGENT';

                return (
                  <div
                    key={item.id}
                    onClick={() => handleSelectMessage(item)}
                    className={`p-4 cursor-pointer transition-colors border-l-4 ${
                      isSelected
                        ? 'bg-[#F2F0FF] border-l-[#5B3FF5]'
                        : 'bg-white hover:bg-gray-50/80 border-l-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          isPersonal 
                            ? 'bg-blue-50 text-blue-700 border border-blue-200' 
                            : 'bg-purple-50 text-purple-700 border border-purple-200'
                        }`}>
                          {isPersonal ? 'Personal' : 'Ruta'}
                        </span>
                        {isUrgent && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                            Urgente
                          </span>
                        )}
                        {!item.read && (
                          <span className="w-2 h-2 rounded-full bg-[#5B3FF5] inline-block" />
                        )}
                      </div>
                      <span className="text-[11px] text-[#A3AAC2] font-mono">
                        {new Date(item.createdAt).toLocaleDateString('es-CO', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>

                    <h4 className={`text-xs font-bold truncate mb-1 ${
                      isSelected ? 'text-[#5B3FF5]' : 'text-[#111827]'
                    }`}>
                      {item.subject}
                    </h4>

                    <p className="text-xs text-[#7C8499] line-clamp-2 leading-relaxed">
                      {item.body}
                    </p>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100 text-[10px] text-[#A3AAC2]">
                      <span className="truncate">{item.sender}</span>
                      {item.replies && item.replies.length > 0 && (
                        <span className="font-semibold text-[#5B3FF5]">
                          {item.replies.length} {item.replies.length === 1 ? 'respuesta' : 'respuestas'}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* PANEL DERECHO: VISOR DE MENSAJE Y CHAT DE RESPUESTA */}
        <div className={`flex-1 bg-white rounded-[24px] border border-[#E2E8F0] shadow-sm flex flex-col overflow-hidden ${
          !showMobileDetail ? 'hidden lg:flex' : 'flex'
        }`}>
          {selectedMessage ? (
            <div className="flex flex-col h-full">
              
              <div className="p-5 border-b border-[#E2E8F0] bg-gray-50/40 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <button
                    type="button"
                    onClick={() => setShowMobileDetail(false)}
                    className="lg:hidden p-1.5 rounded-lg text-[#7C8499] hover:bg-white transition-colors cursor-pointer shrink-0 mt-0.5"
                  >
                    <ArrowLeft size={18} />
                  </button>

                  <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-[#5B3FF5] to-[#7B61FF] text-white flex items-center justify-center font-bold text-sm shadow-md shadow-[#5B3FF5]/20 shrink-0">
                    HSE
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-0.5">
                      <h2 className="text-base sm:text-lg font-bold text-[#111827] truncate">
                        {selectedMessage.subject}
                      </h2>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        selectedMessage.recipientType === 'CODER' 
                          ? 'bg-blue-50 text-blue-700 border border-blue-200' 
                          : 'bg-purple-50 text-purple-700 border border-purple-200'
                      }`}>
                        {selectedMessage.recipientType === 'CODER' ? 'Mensaje Personalizado' : 'Comunicado de Ruta'}
                      </span>
                    </div>

                    <p className="text-xs text-[#7C8499] flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-[#111827]">{selectedMessage.sender}</span>
                      <span>•</span>
                      <span>{selectedMessage.senderRole}</span>
                      <span>•</span>
                      <span className="font-mono text-[#A3AAC2]">
                        {new Date(selectedMessage.createdAt).toLocaleString('es-CO', {
                          dateStyle: 'medium',
                          timeStyle: 'short'
                        })}
                      </span>
                    </p>
                  </div>
                </div>

                {selectedMessage.priority === 'URGENT' && (
                  <span className="text-xs font-bold bg-red-100 text-red-700 px-3 py-1 rounded-full shrink-0">
                    Alta Prioridad
                  </span>
                )}
              </div>

              <div className="flex-1 p-6 overflow-y-auto custom-scrollbar space-y-6">
                
                <div className="bg-[#F8F9FE] border border-[#E8EAF2] rounded-2xl p-5 shadow-2xs">
                  <div className="flex items-center gap-2 text-xs font-bold text-[#5B3FF5] mb-2 uppercase tracking-wide">
                    <ShieldCheck size={16} />
                    <span>Comunicación Oficial HSE Bienestar</span>
                  </div>
                  
                  <div className="text-sm text-[#171B3A] leading-relaxed whitespace-pre-wrap font-normal">
                    {selectedMessage.body}
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#E8EAF2] flex items-center justify-between text-xs text-[#7C8499]">
                    <span>Destinado a: <strong className="text-[#111827]">{selectedMessage.recipientName || selectedMessage.recipientTarget}</strong></span>
                    <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                      <Check size={14} strokeWidth={3} /> Notificación entregada
                    </span>
                  </div>
                </div>

                {selectedMessage.replies && selectedMessage.replies.length > 0 && (
                  <div className="space-y-3 pt-2">
                    <h4 className="text-xs font-bold text-[#7C8499] uppercase tracking-wider flex items-center gap-2">
                      <MessageSquare size={14} className="text-[#5B3FF5]" />
                      Respuestas y Confirmaciones
                    </h4>

                    {selectedMessage.replies.map(rep => (
                      <div 
                        key={rep.id} 
                        className="bg-white border border-[#E2E8F0] p-4 rounded-2xl ml-4 sm:ml-8 shadow-2xs relative"
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-bold text-[#5B3FF5]">{rep.sender}</span>
                          <span className="text-[11px] text-[#A3AAC2] font-mono">
                            {new Date(rep.createdAt).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-xs text-[#111827] leading-relaxed">
                          {rep.body}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

              </div>

              <div className="p-4 border-t border-[#E2E8F0] bg-white">
                <form onSubmit={handleSendReply} className="flex gap-2">
                  <input
                    type="text"
                    value={replyText}
                    onChange={e => setReplyText(e.target.value)}
                    placeholder="Escribe una respuesta o confirmación al equipo HSE..."
                    className="flex-1 px-4 py-2.5 bg-[#F6F7FB] border border-[#E2E8F0] rounded-xl text-xs sm:text-sm focus:border-[#5B3FF5] focus:outline-none focus:bg-white transition-all font-medium"
                  />
                  <button
                    type="submit"
                    className="bg-[#5B3FF5] hover:bg-[#4a32cc] text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-[#5B3FF5]/20 flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
                  >
                    <Send size={15} />
                    <span className="hidden sm:inline">Responder</span>
                  </button>
                </form>
              </div>

            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-[#7C8499]">
              <MessageSquare size={48} className="text-[#5B3FF5] opacity-20 mb-3" />
              <h3 className="text-lg font-bold text-[#111827] mb-1">Ningún mensaje seleccionado</h3>
              <p className="text-xs max-w-xs">
                Selecciona una comunicación del listado a la izquierda para leer las instrucciones completas y responder a HSE.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
