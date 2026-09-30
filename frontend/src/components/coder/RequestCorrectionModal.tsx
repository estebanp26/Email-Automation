import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  AlertTriangle, 
  Send, 
  RefreshCw,
  Clock,
  ShieldAlert
} from 'lucide-react';
import type { CoderJustification, CoderAttachment } from '../../types';
import { EvidenceDropzone, type SelectedFile } from './EvidenceDropzone';
import { updateCoderJustificationWithCorrection } from '../../utils/coderJustifications';

export interface RequestCorrectionModalProps {
  justification: CoderJustification | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (updated: CoderJustification) => void;
}

export function RequestCorrectionModal({
  justification,
  isOpen,
  onClose,
  onSuccess
}: RequestCorrectionModalProps) {
  const [coderReply, setCoderReply] = useState('');
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Resetear el formulario cuando se abre el modal con una nueva justificación
  useEffect(() => {
    if (isOpen) {
      setCoderReply('');
      setFiles([]);
      setErrorMsg(null);
      setIsSubmitting(false);
    }
  }, [isOpen, justification?.radicado]);

  if (!isOpen || !justification) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmedReply = coderReply.trim();
    if (!trimmedReply && files.length === 0) {
      setErrorMsg('Debes ingresar una aclaración escrita o adjuntar al menos un nuevo documento de soporte.');
      return;
    }

    setIsSubmitting(true);

    try {
      // Mapeo de archivos al formato CoderAttachment
      const newAttachments: CoderAttachment[] = files.map(f => ({
        file_id: f.id,
        filename: f.name,
        size_bytes: f.size,
        mime_type: f.type,
        preview_url: f.previewUrl,
        legibility_status: f.legibility,
        legibility_reason: f.legibilityReason,
        storage_path: f.storagePath || `evidences/coder/${f.id}/${f.name}`,
      }));

      const updated = updateCoderJustificationWithCorrection(justification.radicado, {
        newFiles: newAttachments,
        coderReply: trimmedReply,
      });

      if (updated) {
        onSuccess(updated);
        onClose();
      } else {
        setErrorMsg('No se pudo actualizar el radicado. Intenta nuevamente.');
      }
    } catch (err) {
      console.error('Error al subsanar justificación:', err);
      setErrorMsg('Ocurrió un error inesperado al enviar la subsanación.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm"
        />

        {/* Modal Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden z-10 flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-orange-50/50 via-white to-orange-50/20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-orange-100/80 border border-orange-200 text-orange-600 flex items-center justify-center shadow-sm">
                <RefreshCw size={20} className="animate-spin-slow" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                  Subsanar Solicitud
                  <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded-lg bg-orange-100 text-orange-800 border border-orange-200">
                    {justification.radicado}
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Responde a las observaciones del equipo HSE y adjunta nuevos soportes
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              type="button"
              className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
            {/* Observaciones HSE */}
            {justification.hse_notes && (
              <div className="p-4 rounded-2xl bg-orange-50/70 border border-orange-200/80 text-orange-950 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-800">
                  <ShieldAlert size={15} className="text-orange-600" />
                  <span>Observación del Analista HSE:</span>
                </div>
                <p className="text-xs sm:text-sm font-medium leading-relaxed pl-6">
                  {justification.hse_notes}
                </p>
                {justification.hse_reviewer && (
                  <div className="pt-2 text-[11px] text-orange-700/80 flex items-center gap-1 pl-6">
                    <Clock size={12} />
                    <span>Revisado por {justification.hse_reviewer}</span>
                  </div>
                )}
              </div>
            )}

            {/* Resumen de la solicitud original */}
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs text-slate-600 flex flex-wrap gap-x-6 gap-y-2">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Tipo Novedad:</span>
                <span className="font-medium text-slate-800">{justification.novelty_label || justification.novelty_type}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Fechas Reportadas:</span>
                <span className="font-medium text-slate-800">{justification.start_date} al {justification.end_date}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Soportes Previos:</span>
                <span className="font-medium text-slate-800">{justification.attachments?.length || 0} archivo(s)</span>
              </div>
            </div>

            {/* Aclaración / Explicación del Coder */}
            <div className="space-y-1.5">
              <label htmlFor="coderReply" className="block text-xs font-bold text-slate-700">
                Aclaración o mensaje explicativo <span className="text-slate-400 font-normal">(Opcional si adjuntas soporte)</span>
              </label>
              <textarea
                id="coderReply"
                value={coderReply}
                onChange={(e) => setCoderReply(e.target.value)}
                rows={3}
                placeholder="Describe aquí las aclaraciones sobre las fechas, el motivo, o detalles adicionales que solicitó el analista..."
                className="w-full text-xs sm:text-sm p-3.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#5B3FF5] focus:border-transparent transition-all placeholder:text-slate-400 resize-none text-slate-800"
              />
            </div>

            {/* Subida de nuevos archivos de soporte */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700">
                Adjuntar Nuevos Soportes o Evidencias
              </label>
              <EvidenceDropzone
                files={files}
                onFilesChange={setFiles}
                maxFiles={3}
                maxSizeMB={5}
              />
            </div>

            {/* Mensaje de Error */}
            {errorMsg && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertTriangle size={15} className="shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#F97316] to-[#EA580C] hover:opacity-95 text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-orange-500/20 disabled:opacity-50 cursor-pointer transition-all"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    <span>Enviando...</span>
                  </>
                ) : (
                  <>
                    <Send size={14} />
                    <span>Enviar Subsanación</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

export default RequestCorrectionModal;
