import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, Image as ImageIcon, Trash2, AlertCircle, CheckCircle2, Paperclip } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export interface SelectedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
}

interface EvidenceDropzoneProps {
  files: SelectedFile[];
  onFilesChange: (files: SelectedFile[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function EvidenceDropzone({
  files,
  onFilesChange,
  maxFiles = 5,
  maxSizeMB = 10,
}: EvidenceDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = ['pdf', 'png', 'jpg', 'jpeg', 'webp'];

  const validateAndAddFiles = (incomingFiles: FileList | File[]) => {
    setErrorMessage(null);
    const newFilesList: SelectedFile[] = [...files];
    const maxSizeBytes = maxSizeMB * 1024 * 1024;

    for (let i = 0; i < incomingFiles.length; i++) {
      const file = incomingFiles[i];
      const ext = file.name.split('.').pop()?.toLowerCase() || '';

      if (!allowedExtensions.includes(ext)) {
        setErrorMessage(`El archivo "${file.name}" tiene un formato no permitido. Usa PDF, PNG o JPG.`);
        continue;
      }

      if (file.size > maxSizeBytes) {
        setErrorMessage(`El archivo "${file.name}" supera el límite de ${maxSizeMB} MB.`);
        continue;
      }

      if (newFilesList.length >= maxFiles) {
        setErrorMessage(`Has alcanzado el límite máximo de ${maxFiles} archivos adjuntos.`);
        break;
      }

      // Evitar duplicados por nombre y tamaño
      const isDuplicate = newFilesList.some(f => f.name === file.name && f.size === file.size);
      if (!isDuplicate) {
        newFilesList.push({
          id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
          file,
          name: file.name,
          size: file.size,
          type: file.type || ext,
        });
      }
    }

    onFilesChange(newFilesList);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAddFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndAddFiles(e.target.files);
      // Limpiar input para permitir seleccionar el mismo archivo si se eliminó
      e.target.value = '';
    }
  };

  const handleRemoveFile = (id: string) => {
    const updated = files.filter(f => f.id !== id);
    onFilesChange(updated);
    setErrorMessage(null);
  };

  return (
    <div className="space-y-4">
      {/* Zona de Dropzone interactiva */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center relative overflow-hidden group ${
          isDragging
            ? 'border-[#5B3FF5] bg-[#5B3FF5]/10 scale-[1.01]'
            : 'border-white/15 bg-white/[0.03] hover:border-[#5B3FF5]/60 hover:bg-white/[0.05]'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={handleFileInputChange}
        />

        {/* Icono central animado */}
        <div className="size-14 sm:size-16 rounded-2xl bg-[#5B3FF5]/20 border border-[#5B3FF5]/30 flex items-center justify-center text-[#a390fc] group-hover:scale-110 group-hover:text-white group-hover:bg-[#5B3FF5] transition-all shadow-lg shadow-[#5B3FF5]/10 mb-4">
          <UploadCloud className="size-7 sm:size-8" />
        </div>

        <p className="text-sm sm:text-base font-semibold text-white">
          Arrastra y suelta tus evidencias aquí o{' '}
          <span className="text-[#a390fc] underline underline-offset-2 hover:text-white">
            explora tus archivos
          </span>
        </p>

        <p className="text-xs text-slate-400 mt-1.5 max-w-md">
          Soporta certificados médicos, fórmulas, radicados o tickets en formato{' '}
          <span className="text-slate-300 font-medium">PDF, PNG, JPG</span> (máximo {maxSizeMB} MB por archivo, hasta {maxFiles} archivos).
        </p>

        <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400 bg-white/5 px-3 py-1 rounded-full border border-white/10">
          <Paperclip className="size-3 text-[#5B3FF5]" />
          <span>{files.length} de {maxFiles} archivos cargados</span>
        </div>
      </div>

      {/* Alerta de error si el archivo no cumplió condiciones */}
      {errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium"
        >
          <AlertCircle className="size-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </motion.div>
      )}

      {/* Listado de Archivos Seleccionados */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-300 px-1">
          <span>Archivos listos para enviar ({files.length}):</span>
          {files.length > 0 && (
            <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-mono">
              <CheckCircle2 className="size-3" />
              Soporte adjunto
            </span>
          )}
        </div>

        {files.length === 0 ? (
          <div className="py-6 px-4 text-center rounded-xl bg-white/[0.02] border border-white/5 text-slate-400 text-xs">
            No has seleccionado ningún archivo probatorio aún. Puedes continuar sin adjuntos o cargar tus evidencias.
          </div>
        ) : (
          <AnimatePresence>
            {files.map((item) => {
              const isPdf = item.name.toLowerCase().endsWith('.pdf');
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-center justify-between p-3 sm:p-3.5 rounded-xl bg-[#171B3A] border border-white/10 hover:border-white/20 transition-all shadow-sm group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`size-10 rounded-lg flex items-center justify-center shrink-0 border ${
                        isPdf
                          ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                          : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                      }`}
                    >
                      {isPdf ? <FileText className="size-5" /> : <ImageIcon className="size-5" />}
                    </div>

                    <div className="min-w-0">
                      <p className="text-xs sm:text-sm font-semibold text-white truncate max-w-[280px] sm:max-w-md">
                        {item.name}
                      </p>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {formatFileSize(item.size)} · <span className="uppercase text-slate-400">{isPdf ? 'PDF' : 'IMAGEN'}</span>
                      </p>
                    </div>
                  </div>

                  {/* Botón eliminar archivo */}
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(item.id)}
                    className="size-8 rounded-lg bg-white/5 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-white/10 hover:border-rose-500/30 flex items-center justify-center transition-all cursor-pointer shrink-0 ml-3"
                    title="Eliminar este archivo"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
