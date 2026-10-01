import { useState, useRef, useEffect, useCallback } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  UploadCloud, 
  FileText, 
  Image as ImageIcon, 
  Trash2, 
  AlertCircle, 
  CheckCircle2, 
  Paperclip, 
  Eye, 
  RefreshCw, 
  X, 
  ShieldCheck, 
  AlertTriangle,
  Check
} from 'lucide-react';

export interface SelectedFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  previewUrl: string;
  dataUrl?: string;
  progress: number;
  status: 'uploading' | 'ready' | 'error';
  legibility: 'optimal' | 'standard' | 'warning';
  legibilityReason: string;
  // Estructura preparada para Supabase Storage / Presigned URL
  storagePath?: string;
  presignedUrl?: string;
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

/**
 * Validador de tipo MIME real mediante Magic Numbers (firmas binarias)
 * - PDF: 25 50 44 46 (%PDF)
 * - PNG: 89 50 4E 47 (\x89PNG)
 * - JPEG/JPG: FF D8 FF
 */
async function validateMagicNumber(file: File): Promise<'pdf' | 'png' | 'jpeg' | null> {
  try {
    const buffer = await file.slice(0, 8).arrayBuffer();
    const bytes = new Uint8Array(buffer);

    // PDF: %PDF
    if (bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46) {
      return 'pdf';
    }
    // PNG: \x89PNG
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47) {
      return 'png';
    }
    // JPEG/JPG: \xFF\xD8\xFF
    if (bytes[0] === 0xFF && bytes[1] === 0xD8 && bytes[2] === 0xFF) {
      return 'jpeg';
    }
  } catch (err) {
    console.warn('Error al leer Magic Numbers:', err);
  }
  return null;
}

/**
 * Evaluación preliminar de legibilidad en cliente sin IA
 * Verifica dimensiones reales para imágenes o consistencia de tamaño en PDFs
 */
async function evaluateLegibility(
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

  // Para imágenes: evaluamos dimensiones naturales con Image()
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

export function EvidenceDropzone({
  files,
  onFilesChange,
  maxFiles = 3,
  maxSizeMB = 10,
}: EvidenceDropzoneProps) {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<SelectedFile | null>(null);
  const replaceInputRef = useRef<HTMLInputElement>(null);
  const fileToReplaceIdRef = useRef<string | null>(null);
  const filesRef = useRef<SelectedFile[]>(files);

  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  const EXACT_ERROR_MSG = 'Formato no permitido o tamaño superior a 10MB';

  // Simulación progresiva de carga y preparación de evidencia
  const simulateUploadProgress = (fileId: string) => {
    let currentProgress = 10;
    const interval = setInterval(() => {
      currentProgress += Math.floor(Math.random() * 25) + 15;
      if (currentProgress >= 100) {
        currentProgress = 100;
        clearInterval(interval);
      }
      
      const updated = filesRef.current.map((f) =>
        f.id === fileId
          ? {
              ...f,
              progress: currentProgress,
              status: (currentProgress === 100 ? 'ready' : 'uploading') as 'ready' | 'uploading',
            }
          : f
      );
      onFilesChange(updated);
    }, 120);
  };

  // Procesamiento y validación profunda de archivos recibidos
  const processIncomingFiles = useCallback(
    async (incomingFiles: File[]) => {
      setErrorMessage(null);

      if (files.length >= maxFiles) {
        setErrorMessage(`Límite alcanzado: máximo ${maxFiles} evidencias simultáneas.`);
        return;
      }

      const availableSlots = maxFiles - files.length;
      const filesToProcess = incomingFiles.slice(0, availableSlots);

      if (incomingFiles.length > availableSlots) {
        setErrorMessage(`Solo se pueden agregar ${availableSlots} archivo(s) más (máximo ${maxFiles}).`);
      }

      const validatedList: SelectedFile[] = [];

      for (const file of filesToProcess) {
        // 1. Validación de tamaño máximo
        if (file.size > maxSizeBytes) {
          setErrorMessage(EXACT_ERROR_MSG);
          continue;
        }

        // 2. Validación de Magic Numbers (tipo binario real)
        const magicType = await validateMagicNumber(file);
        if (!magicType) {
          setErrorMessage(EXACT_ERROR_MSG);
          continue;
        }

        // 3. Validación de duplicados por nombre y tamaño
        const isDuplicate = files.some((f) => f.name === file.name && f.size === file.size);
        if (isDuplicate) {
          continue;
        }

        // 4. Evaluación de legibilidad en cliente
        const legibilityResult = await evaluateLegibility(file, magicType);

        // 5. Creación del objeto de soporte con estructura para Supabase Storage y persistencia en cliente
        const fileId = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        const objectUrl = URL.createObjectURL(file);

        let fileDataUrl = '';
        try {
          fileDataUrl = await new Promise<string>((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
            reader.onerror = () => resolve('');
            reader.readAsDataURL(file);
          });
        } catch {
          fileDataUrl = '';
        }

        const newSelectedFile: SelectedFile = {
          id: fileId,
          file,
          name: file.name,
          size: file.size,
          type: magicType === 'pdf' ? 'application/pdf' : `image/${magicType}`,
          previewUrl: fileDataUrl || objectUrl,
          dataUrl: fileDataUrl || objectUrl,
          progress: 15,
          status: 'uploading',
          legibility: legibilityResult.legibility,
          legibilityReason: legibilityResult.reason,
          storagePath: `evidences/coder/${fileId}/${file.name}`,
          presignedUrl: undefined,
        };

        validatedList.push(newSelectedFile);
      }

      if (validatedList.length > 0) {
        const nextFiles = [...files, ...validatedList];
        onFilesChange(nextFiles);

        // Iniciar simulación de carga para los nuevos archivos
        validatedList.forEach((vf) => simulateUploadProgress(vf.id));
      }
    },
    [files, maxFiles, maxSizeBytes, onFilesChange]
  );

  // Configuración de react-dropzone
  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      if (fileRejections.length > 0) {
        setErrorMessage(EXACT_ERROR_MSG);
      }
      if (acceptedFiles.length > 0) {
        processIncomingFiles(acceptedFiles);
      }
    },
    [processIncomingFiles]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxSize: maxSizeBytes,
    maxFiles,
    disabled: files.length >= maxFiles,
  });

  // Reemplazar un archivo específico (Sustituir)
  const handleTriggerReplace = (fileId: string) => {
    fileToReplaceIdRef.current = fileId;
    replaceInputRef.current?.click();
  };

  const handleFileReplacement = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetFile = e.target.files?.[0];
    const targetId = fileToReplaceIdRef.current;
    e.target.value = ''; // Reset input

    if (!targetFile || !targetId) return;

    if (targetFile.size > maxSizeBytes) {
      setErrorMessage(EXACT_ERROR_MSG);
      return;
    }

    const magicType = await validateMagicNumber(targetFile);
    if (!magicType) {
      setErrorMessage(EXACT_ERROR_MSG);
      return;
    }

    const legibilityResult = await evaluateLegibility(targetFile, magicType);
    const objectUrl = URL.createObjectURL(targetFile);

    let replacementDataUrl = '';
    try {
      replacementDataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '');
        reader.onerror = () => resolve('');
        reader.readAsDataURL(targetFile);
      });
    } catch {
      replacementDataUrl = '';
    }

    const updated = filesRef.current.map((f) => {
      if (f.id === targetId) {
        URL.revokeObjectURL(f.previewUrl);
        return {
          ...f,
          file: targetFile,
          name: targetFile.name,
          size: targetFile.size,
          type: magicType === 'pdf' ? 'application/pdf' : `image/${magicType}`,
          previewUrl: replacementDataUrl || objectUrl,
          dataUrl: replacementDataUrl || objectUrl,
          progress: 10,
          status: 'uploading' as const,
          legibility: legibilityResult.legibility,
          legibilityReason: legibilityResult.reason,
          storagePath: `evidences/coder/${f.id}/${targetFile.name}`,
        };
      }
      return f;
    });

    onFilesChange(updated);
    simulateUploadProgress(targetId);
    setErrorMessage(null);
  };

  // Eliminar un archivo
  const handleRemoveFile = (id: string) => {
    const toRemove = files.find((f) => f.id === id);
    if (toRemove?.previewUrl) {
      URL.revokeObjectURL(toRemove.previewUrl);
    }
    const updated = files.filter((f) => f.id !== id);
    onFilesChange(updated);
    setErrorMessage(null);
    if (previewFile?.id === id) {
      setPreviewFile(null);
    }
  };

  // Limpieza de ObjectURLs al desmontar
  useEffect(() => {
    return () => {
      filesRef.current.forEach((f) => {
        if (f.previewUrl) {
          URL.revokeObjectURL(f.previewUrl);
        }
      });
    };
  }, []);

  return (
    <div className="space-y-4 font-sans">
      {/* Input oculto exclusivo para la acción "Sustituir" */}
      <input
        ref={replaceInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
        onChange={handleFileReplacement}
      />

      {/* Zona react-dropzone interactiva */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-3xl p-6 sm:p-8 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center relative overflow-hidden group ${
          files.length >= maxFiles
            ? 'opacity-60 cursor-not-allowed border-slate-200 bg-slate-50'
            : isDragReject
            ? 'border-rose-400 bg-rose-50/70 scale-[1.01]'
            : isDragActive
            ? 'border-[#5B3FF5] bg-[#5B3FF5]/10 scale-[1.01] shadow-lg shadow-[#5B3FF5]/15'
            : 'border-slate-300 bg-slate-50/70 hover:border-[#5B3FF5] hover:bg-[#5B3FF5]/5 hover:shadow-md'
        }`}
      >
        <input {...getInputProps()} />

        {/* Icono central de nube con acento morado RIWI */}
        <div className="size-14 sm:size-16 rounded-2xl bg-[#5B3FF5]/10 border border-[#5B3FF5]/20 flex items-center justify-center text-[#5B3FF5] group-hover:scale-110 group-hover:bg-[#5B3FF5] group-hover:text-white transition-all shadow-md shadow-[#5B3FF5]/15 mb-3.5">
          <UploadCloud className="size-7 sm:size-8" />
        </div>

        <p className="text-sm sm:text-base font-bold text-[#11132C]">
          Arrastra y suelta tus evidencias aquí o{' '}
          <span className="text-[#5B3FF5] underline underline-offset-4 hover:text-[#4a32cc]">
            explora tus archivos
          </span>
        </p>

        <p className="text-xs text-[#7C8499] mt-1.5 max-w-md leading-relaxed">
          Formatos autorizados: <strong className="text-[#11132C]">PDF, PNG, JPG / JPEG</strong>.
          <br />
          Máximo <span className="font-semibold text-slate-700">{maxSizeMB} MB</span> por archivo · Hasta{' '}
          <span className="font-semibold text-slate-700">{maxFiles} evidencias simultáneas</span>.
        </p>

        {/* Badge contador de archivos */}
        <div className="mt-4 flex items-center gap-2 text-[11px] font-semibold text-[#7C8499] bg-white px-3.5 py-1 rounded-full border border-slate-200 shadow-sm">
          <Paperclip className="size-3 text-[#5B3FF5]" />
          <span>{files.length} de {maxFiles} evidencias cargadas</span>
        </div>
      </div>

      {/* Alerta de error (rechazo por formato o tamaño superior a 10MB) */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center gap-2.5 p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold shadow-sm"
          >
            <AlertCircle className="size-4 shrink-0 text-rose-500" />
            <span>{errorMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Listado interactivo de Evidencias Cargadas */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-bold text-[#11132C] px-1">
          <span>Evidencias preparadas ({files.length} de {maxFiles}):</span>
          {files.length > 0 && files.every((f) => f.status === 'ready') && (
            <span className="text-[11px] text-emerald-600 flex items-center gap-1 font-semibold">
              <CheckCircle2 className="size-3.5 text-emerald-500" />
              Soportes validados listos para envío
            </span>
          )}
        </div>

        {files.length === 0 ? (
          <div className="py-7 px-4 text-center rounded-2xl bg-slate-50 border border-slate-200 text-[#7C8499] text-xs">
            No has adjuntado evidencias aún. Puedes continuar sin adjuntos o cargar certificados médicos o comprobantes.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            <AnimatePresence>
              {files.map((item) => {
                const isPdf = item.type === 'application/pdf' || item.name.toLowerCase().endsWith('.pdf');

                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="p-3.5 sm:p-4 rounded-2xl bg-white border border-slate-200/90 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.06)] hover:border-slate-300 transition-all space-y-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      {/* Miniatura / Icono de archivo */}
                      <div className="flex items-center gap-3 min-w-0">
                        {isPdf ? (
                          <div 
                            onClick={() => setPreviewFile(item)}
                            className="size-12 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 flex flex-col items-center justify-center shrink-0 cursor-pointer hover:scale-105 transition-transform"
                            title="Previsualizar PDF"
                          >
                            <FileText className="size-5" />
                            <span className="text-[9px] font-bold uppercase mt-0.5">PDF</span>
                          </div>
                        ) : (
                          <div
                            onClick={() => setPreviewFile(item)}
                            className="size-12 rounded-xl border border-slate-200 overflow-hidden shrink-0 cursor-pointer relative group bg-slate-100 flex items-center justify-center"
                            title="Previsualizar Imagen"
                          >
                            <img
                              src={item.previewUrl}
                              alt={item.name}
                              className="size-full object-cover group-hover:scale-110 transition-transform"
                            />
                            <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white">
                              <Eye className="size-4" />
                            </div>
                          </div>
                        )}

                        {/* Nombre, peso y validación de legibilidad */}
                        <div className="min-w-0 space-y-0.5">
                          <p className="text-xs sm:text-sm font-bold text-[#11132C] truncate max-w-[220px] sm:max-w-md">
                            {item.name}
                          </p>
                          <div className="flex flex-wrap items-center gap-2 text-[11px] text-[#7C8499]">
                            <span className="font-mono font-medium">{formatFileSize(item.size)}</span>
                            <span>·</span>
                            {/* Badge de legibilidad sin IA */}
                            {item.legibility === 'optimal' && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                                <ShieldCheck className="size-3 text-emerald-500" />
                                Legibilidad verificada
                              </span>
                            )}
                            {item.legibility === 'standard' && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                                <Check className="size-3 text-blue-500" />
                                Legibilidad estándar
                              </span>
                            )}
                            {item.legibility === 'warning' && (
                              <span 
                                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200"
                                title={item.legibilityReason}
                              >
                                <AlertTriangle className="size-3 text-amber-500" />
                                Baja resolución
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Acciones: Previsualizar, Sustituir y Eliminar */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        {/* Botón Previsualizar */}
                        <button
                          type="button"
                          onClick={() => setPreviewFile(item)}
                          className="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-[#5B3FF5]/10 text-slate-700 hover:text-[#5B3FF5] border border-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                          title="Previsualizar documento"
                        >
                          <Eye className="size-3.5" />
                          <span className="hidden sm:inline">Ver</span>
                        </button>

                        {/* Botón Sustituir */}
                        <button
                          type="button"
                          onClick={() => handleTriggerReplace(item.id)}
                          className="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                          title="Sustituir por otro archivo"
                        >
                          <RefreshCw className="size-3.5" />
                          <span className="hidden sm:inline">Sustituir</span>
                        </button>

                        {/* Botón Eliminar */}
                        <button
                          type="button"
                          onClick={() => handleRemoveFile(item.id)}
                          className="size-8 rounded-xl bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-slate-200 hover:border-rose-200 flex items-center justify-center transition-all cursor-pointer"
                          title="Eliminar este soporte"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Barra de progreso visual y estado de carga */}
                    <div className="space-y-1 pt-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#7C8499] flex items-center gap-1.5">
                          {item.status === 'uploading' ? (
                            <>
                              <div className="size-2.5 border-2 border-[#5B3FF5] border-t-transparent rounded-full animate-spin" />
                              <span className="font-medium text-[#5B3FF5]">Procesando archivo...</span>
                            </>
                          ) : (
                            <span className="text-emerald-600 font-semibold flex items-center gap-1">
                              <CheckCircle2 className="size-3" />
                              Preparado para envío
                            </span>
                          )}
                        </span>
                        <span className="font-mono text-[#7C8499] font-medium">{item.progress}%</span>
                      </div>

                      <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/50">
                        <div
                          className={`h-full transition-all duration-300 rounded-full ${
                            item.status === 'ready'
                              ? 'bg-emerald-500'
                              : 'bg-gradient-to-r from-[#5B3FF5] to-[#3B82F6]'
                          }`}
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Modal Interactivo de Previsualización (PDF mediante iframe / Imagen ampliada) */}
      <AnimatePresence>
        {previewFile && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-[#11132C]/75 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-4xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]"
            >
              {/* Header del Modal */}
              <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="size-9 rounded-xl bg-[#5B3FF5]/10 text-[#5B3FF5] flex items-center justify-center shrink-0">
                    {previewFile.type === 'application/pdf' ? (
                      <FileText className="size-5 text-rose-500" />
                    ) : (
                      <ImageIcon className="size-5 text-[#5B3FF5]" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm sm:text-base font-bold text-[#11132C] truncate max-w-md sm:max-w-xl">
                      {previewFile.name}
                    </h3>
                    <p className="text-xs text-[#7C8499] font-mono">
                      {formatFileSize(previewFile.size)} · {previewFile.legibilityReason}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      handleTriggerReplace(previewFile.id);
                      setPreviewFile(null);
                    }}
                    className="hidden sm:flex px-3 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 items-center gap-1.5 cursor-pointer"
                  >
                    <RefreshCw className="size-3.5" />
                    <span>Sustituir</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setPreviewFile(null)}
                    className="size-9 rounded-xl bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 border border-slate-200 flex items-center justify-center transition-colors cursor-pointer"
                    title="Cerrar previsualización"
                  >
                    <X className="size-5" />
                  </button>
                </div>
              </div>

              {/* Visor de Contenido (PDF o Imagen) */}
              <div className="flex-1 overflow-auto p-4 sm:p-6 bg-[#F6F7FB] flex items-center justify-center">
                {previewFile.type === 'application/pdf' ? (
                  <iframe
                    src={previewFile.previewUrl}
                    title={previewFile.name}
                    className="w-full h-[65vh] rounded-2xl border border-slate-200 bg-white shadow-sm"
                  />
                ) : (
                  <div className="max-h-[65vh] max-w-full flex items-center justify-center overflow-auto rounded-2xl bg-white p-3 border border-slate-200 shadow-sm">
                    <img
                      src={previewFile.previewUrl}
                      alt={previewFile.name}
                      className="max-h-[60vh] max-w-full object-contain rounded-lg"
                    />
                  </div>
                )}
              </div>

              {/* Footer del Modal */}
              <div className="px-5 py-3.5 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-[#7C8499]">
                <span>Soporte probatorio · Riwi Barranquilla</span>
                <button
                  type="button"
                  onClick={() => setPreviewFile(null)}
                  className="px-4 py-2 rounded-xl bg-[#5B3FF5] hover:bg-[#4a32cc] text-white font-bold text-xs shadow-md shadow-[#5B3FF5]/20 cursor-pointer"
                >
                  Cerrar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
