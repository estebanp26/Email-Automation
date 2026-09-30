import { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowRight, 
  ArrowLeft, 
  ShieldCheck, 
  Stethoscope, 
  HeartHandshake, 
  Scale, 
  WifiOff, 
  GraduationCap, 
  HelpCircle, 
  Send, 
  Sparkles,
  RefreshCw
} from 'lucide-react';
import { 
  excuseFormSchema, 
  type ExcuseFormData, 
  NOVELTY_TYPES, 
  type NoveltyTypeId 
} from '../../schemas/excuseValidationSchema';
import { EvidenceDropzone, type SelectedFile } from '../../components/coder/EvidenceDropzone';
import { getCoderSession } from '../../components/coder/CoderLayout';

export default function ExcuseSubmissionForm() {
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionSuccess, setSubmissionSuccess] = useState<null | {
    radicadoId: string;
    submittedAt: string;
    data: ExcuseFormData;
    filesCount: number;
  }>(null);

  const session = useMemo(() => getCoderSession(), []);

  // Configuración de React Hook Form + Zod
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
    trigger,
  } = useForm<ExcuseFormData>({
    resolver: zodResolver(excuseFormSchema),
    mode: 'onChange',
    defaultValues: {
      novelty_type: 'incapacidad_medica',
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0],
      description: '',
      truth_declaration: false,
    },
  });

  const selectedType = watch('novelty_type');
  const descriptionValue = watch('description') || '';
  const charCount = descriptionValue.length;

  // Metadata contextual del tipo de novedad seleccionado
  const activeNoveltyInfo = useMemo(() => {
    return NOVELTY_TYPES.find(t => t.id === selectedType) || NOVELTY_TYPES[0];
  }, [selectedType]);

  // Manejador del avance hacia el Paso 2 (Evidencias)
  const handleProceedToEvidence = async () => {
    const valid = await trigger();
    if (valid) {
      setCurrentStep(2);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Manejador de envío final simulado (preparado para backend)
  const onSubmitFinal = async (data: ExcuseFormData) => {
    setIsSubmitting(true);
    
    setTimeout(() => {
      const radNumber = `RAD-HSE-${new Date().getFullYear()}-${Math.floor(100000 + Math.random() * 900000)}`;
      
      const payloadReadyForBackend = {
        radicado: radNumber,
        coder_id: session.id,
        coder_cedula: session.cedula,
        coder_name: session.name,
        coder_email: session.email,
        academic_route: session.route,
        novelty_type: data.novelty_type,
        start_date: data.start_date,
        end_date: data.end_date,
        description: data.description,
        truth_declaration: data.truth_declaration,
        attachments: selectedFiles.map(f => ({
          filename: f.name,
          size_bytes: f.size,
          mime_type: f.type,
        })),
        submitted_at: new Date().toISOString(),
      };

      console.log('Payload estructurado para el Backend:', payloadReadyForBackend);

      setSubmissionSuccess({
        radicadoId: radNumber,
        submittedAt: new Date().toLocaleString('es-CO', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }),
        data,
        filesCount: selectedFiles.length,
      });

      setIsSubmitting(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 900);
  };

  const getNoveltyIcon = (id: NoveltyTypeId) => {
    switch (id) {
      case 'incapacidad_medica':
        return <Stethoscope className="size-4 text-emerald-500" />;
      case 'calamidad_domestica':
        return <HeartHandshake className="size-4 text-amber-500" />;
      case 'tramite_legal':
        return <Scale className="size-4 text-sky-500" />;
      case 'falla_tecnica':
        return <WifiOff className="size-4 text-orange-500" />;
      case 'permiso_academico_otro':
        return <GraduationCap className="size-4 text-[#5B3FF5]" />;
      default:
        return <HelpCircle className="size-4 text-slate-400" />;
    }
  };

  // Pantalla de Confirmación Exitosa
  if (submissionSuccess) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-2xl mx-auto p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/90 shadow-[0_10px_40px_-15px_rgba(0,0,0,0.1)] relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
          <Sparkles className="size-48 text-[#5B3FF5]" />
        </div>

        <div className="size-16 sm:size-20 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-6 mx-auto shadow-md shadow-emerald-500/10">
          <CheckCircle2 className="size-10 sm:size-12" />
        </div>

        <div className="text-center space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 font-mono">
            Reporte Radicado Exitosamente
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#11132C]">
            ¡Tu justificación ha sido enviada!
          </h2>
          <p className="text-sm text-[#7C8499] max-w-md mx-auto">
            El equipo de <strong className="text-[#11132C]">Habilidades para la Vida (HSE)</strong> revisará tu reporte y recibirás la notificación de respuesta en tu correo institucional.
          </p>
        </div>

        {/* Resumen del Radicado */}
        <div className="mt-8 p-6 rounded-2xl bg-slate-50 border border-slate-200 space-y-3.5 text-xs sm:text-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <span className="text-[#7C8499]">Número de Radicado:</span>
            <span className="font-mono font-bold text-[#5B3FF5] bg-[#5B3FF5]/10 px-3 py-1 rounded-lg border border-[#5B3FF5]/20">
              {submissionSuccess.radicadoId}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Coder:</span>
            <span className="font-semibold text-[#11132C]">{session.name} ({session.cedula})</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Tipo de Novedad:</span>
            <span className="font-medium text-[#11132C] capitalize">
              {activeNoveltyInfo.label}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Periodo reportado:</span>
            <span className="font-medium text-[#11132C]">
              {submissionSuccess.data.start_date} al {submissionSuccess.data.end_date}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Evidencias adjuntas:</span>
            <span className="font-medium text-emerald-600 font-semibold">
              {submissionSuccess.filesCount} archivo(s) registrado(s)
            </span>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-slate-200 text-[11px] text-[#7C8499]">
            <span>Fecha y hora de registro:</span>
            <span className="font-mono">{submissionSuccess.submittedAt}</span>
          </div>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setSubmissionSuccess(null);
              setCurrentStep(1);
              setSelectedFiles([]);
            }}
            className="w-full sm:flex-1 py-3.5 px-4 rounded-xl bg-[#5B3FF5] hover:bg-[#4a32cc] text-white font-semibold text-sm transition-all shadow-lg shadow-[#5B3FF5]/30 flex items-center justify-center gap-2 cursor-pointer"
          >
            <RefreshCw className="size-4" />
            Radicar otra Justificación
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Banner de Bienvenida del Coder */}
      <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-[0_4px_25px_-10px_rgba(0,0,0,0.05)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="size-2 rounded-full bg-emerald-500 animate-ping" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#5B3FF5]">
              Reporte de Justificaciones
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#11132C] tracking-tight">
            Hola, {session.name.split(' ')[0]} 👋
          </h1>
          <p className="text-xs sm:text-sm text-[#7C8499] max-w-xl">
            Registra tu novedad de inasistencia o tardanza con los soportes requeridos para que el equipo HSE mantenga al día tu trazabilidad formativa.
          </p>
        </div>

        {/* Stepper Visual */}
        <div className="flex items-center gap-2 bg-slate-50 p-1.5 rounded-2xl border border-slate-200 self-stretch sm:self-auto justify-center">
          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
              currentStep === 1
                ? 'bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/30'
                : 'text-[#7C8499] hover:text-[#11132C] cursor-pointer'
            }`}
            onClick={() => setCurrentStep(1)}
          >
            <span className={`size-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
              currentStep === 1 ? 'bg-white/20 text-white' : 'bg-slate-200 text-[#7C8499]'
            }`}>
              1
            </span>
            <span>Motivo</span>
          </div>

          <div className="h-4 w-px bg-slate-200" />

          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
              currentStep === 2
                ? 'bg-[#5B3FF5] text-white shadow-md shadow-[#5B3FF5]/30'
                : 'text-[#7C8499]'
            }`}
          >
            <span className={`size-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
              currentStep === 2 ? 'bg-white/20 text-white' : 'bg-slate-200 text-[#7C8499]'
            }`}>
              2
            </span>
            <span>Evidencias</span>
          </div>
        </div>
      </div>

      {/* Contenedor del Formulario con transiciones */}
      <form onSubmit={handleSubmit(onSubmitFinal)} className="space-y-6">
        <AnimatePresence mode="wait">
          {currentStep === 1 ? (
            /* ========================================================
               PASO 1: MOTIVO, FECHAS Y DESCRIPCIÓN
               ======================================================== */
            <motion.div
              key="step-1"
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 16 }}
              transition={{ duration: 0.2 }}
              className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-[0_4px_25px_-10px_rgba(0,0,0,0.06)] space-y-6"
            >
              <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-[#11132C] flex items-center gap-2">
                    <FileText className="size-5 text-[#5B3FF5]" />
                    Paso 1: Detalle del Motivo de Inasistencia
                  </h2>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    Selecciona el tipo de evento e indica las fechas exactas de la ausencia.
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold text-[#5B3FF5] bg-[#5B3FF5]/10 px-2.5 py-1 rounded-lg border border-[#5B3FF5]/20">
                  Paso 1 de 2
                </span>
              </div>

              {/* 1. Selector de Tipo de Novedad */}
              <div className="space-y-2.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-[#11132C]">
                  Tipo de Novedad <span className="text-rose-500">*</span>
                </label>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {NOVELTY_TYPES.map((type) => {
                    const isSelected = selectedType === type.id;
                    return (
                      <button
                        key={type.id}
                        type="button"
                        onClick={() => setValue('novelty_type', type.id, { shouldValidate: true })}
                        className={`p-3.5 rounded-2xl text-left border transition-all cursor-pointer flex flex-col justify-between group ${
                          isSelected
                            ? 'bg-[#5B3FF5]/5 border-[#5B3FF5] shadow-md shadow-[#5B3FF5]/10 ring-2 ring-[#5B3FF5]/20'
                            : 'bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-slate-100/60'
                        }`}
                      >
                        <div className="flex items-center justify-between w-full mb-2">
                          <div className="flex items-center gap-2">
                            {getNoveltyIcon(type.id)}
                            <span className="text-xs font-bold text-[#11132C]">
                              {type.label}
                            </span>
                          </div>
                          <span
                            className={`size-4 rounded-full border flex items-center justify-center ${
                              isSelected
                                ? 'border-[#5B3FF5] bg-[#5B3FF5]'
                                : 'border-slate-300 bg-white'
                            }`}
                          >
                            {isSelected && <span className="size-1.5 rounded-full bg-white" />}
                          </span>
                        </div>
                        <p className="text-[11px] text-[#7C8499] leading-relaxed line-clamp-2">
                          {type.hint}
                        </p>
                      </button>
                    );
                  })}
                </div>
                {errors.novelty_type && (
                  <p className="text-xs text-rose-500 font-medium">{errors.novelty_type.message}</p>
                )}
              </div>

              {/* 2. Caja de Alerta Contextual Dinámica */}
              <motion.div
                key={activeNoveltyInfo.id}
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="p-4 rounded-2xl bg-[#5B3FF5]/5 border border-[#5B3FF5]/20 flex items-start gap-3 text-xs"
              >
                <AlertTriangle className="size-4 shrink-0 text-[#5B3FF5] mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-bold text-[#5B3FF5] uppercase tracking-wide text-[10px]">
                    Criterio HSE para {activeNoveltyInfo.label}
                  </span>
                  <p className="text-slate-700 leading-relaxed">
                    {activeNoveltyInfo.alert}
                  </p>
                </div>
              </motion.div>

              {/* 3. Fechas de Inicio y Fin */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#11132C]">
                    Fecha de Inicio <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      {...register('start_date')}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[#11132C] text-xs sm:text-sm focus:outline-none focus:border-[#5B3FF5] focus:bg-white focus:ring-2 focus:ring-[#5B3FF5]/20 transition-all font-mono"
                    />
                  </div>
                  {errors.start_date && (
                    <p className="text-xs text-rose-500 font-medium">{errors.start_date.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#11132C]">
                    Fecha de Finalización <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      {...register('end_date')}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[#11132C] text-xs sm:text-sm focus:outline-none focus:border-[#5B3FF5] focus:bg-white focus:ring-2 focus:ring-[#5B3FF5]/20 transition-all font-mono"
                    />
                  </div>
                  {errors.end_date && (
                    <p className="text-xs text-rose-500 font-medium">{errors.end_date.message}</p>
                  )}
                </div>
              </div>

              {/* 4. Descripción Detallada con Contador */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#11132C]">
                    Descripción Detallada del Motivo <span className="text-rose-500">*</span>
                  </label>
                  <span
                    className={`text-xs font-mono font-bold ${
                      charCount < 30
                        ? 'text-rose-500'
                        : charCount > 1500
                        ? 'text-rose-500'
                        : 'text-[#7C8499]'
                    }`}
                  >
                    {charCount} / 1500 caracteres
                  </span>
                </div>

                <textarea
                  rows={4}
                  placeholder="Explica detalladamente la causa de tu ausencia, los síntomas o la situación presentada..."
                  {...register('description')}
                  className="w-full p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-[#11132C] text-xs sm:text-sm placeholder:text-[#7C8499] focus:outline-none focus:border-[#5B3FF5] focus:bg-white focus:ring-2 focus:ring-[#5B3FF5]/20 transition-all resize-none leading-relaxed"
                />

                <div className="flex items-center justify-between text-[11px] text-[#7C8499]">
                  <span>Mínimo 30 caracteres para brindar contexto suficiente al equipo HSE.</span>
                  {charCount > 0 && charCount < 30 && (
                    <span className="text-rose-500 font-medium">
                      Faltan {30 - charCount} caracteres
                    </span>
                  )}
                </div>

                {errors.description && (
                  <p className="text-xs text-rose-500 font-medium">{errors.description.message}</p>
                )}
              </div>

              {/* 5. Declaración de Veracidad Obligatoria */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                <label className="flex items-start gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    {...register('truth_declaration')}
                    className="size-4 rounded mt-0.5 accent-[#5B3FF5] cursor-pointer"
                  />
                  <span className="text-xs text-slate-700 leading-relaxed">
                    <strong className="text-[#11132C]">Declaración bajo gravedad de juramento:</strong> Declaro
                    que la información suministrada y los soportes adjuntos son verídicos, auténticos y corresponden a mi situación particular durante las fechas indicadas.
                  </span>
                </label>
                {errors.truth_declaration && (
                  <p className="text-xs text-rose-500 font-medium pl-7">
                    {errors.truth_declaration.message}
                  </p>
                )}
              </div>

              {/* 6. Botón Continuar con Evidencias */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={handleProceedToEvidence}
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#5B3FF5] hover:bg-[#4a32cc] text-white font-bold text-xs sm:text-sm transition-all shadow-lg shadow-[#5B3FF5]/30 flex items-center justify-center gap-2 cursor-pointer"
                >
                  <span>Continuar con Evidencias</span>
                  <ArrowRight className="size-4" />
                </button>
              </div>
            </motion.div>
          ) : (
            /* ========================================================
               PASO 2: CARGA VISUAL DE EVIDENCIAS Y CONFIRMACIÓN
               ======================================================== */
            <motion.div
              key="step-2"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.2 }}
              className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200/80 shadow-[0_4px_25px_-10px_rgba(0,0,0,0.06)] space-y-6"
            >
              <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-[#11132C] flex items-center gap-2">
                    <ShieldCheck className="size-5 text-[#5B3FF5]" />
                    Paso 2: Adjuntar Soportes Probatorios
                  </h2>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    Adjunta los certificados médicos, capturas o radicados que respaldan tu justificación.
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold text-[#5B3FF5] bg-[#5B3FF5]/10 px-2.5 py-1 rounded-lg border border-[#5B3FF5]/20">
                  Paso 2 de 2
                </span>
              </div>

              {/* Resumen compacto del Paso 1 */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center shadow-sm">
                    {getNoveltyIcon(selectedType)}
                  </div>
                  <div>
                    <p className="font-bold text-[#11132C]">{activeNoveltyInfo.label}</p>
                    <p className="text-[#7C8499] font-mono text-[11px]">
                      Periodo: {watch('start_date')} al {watch('end_date')}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="text-xs font-semibold text-[#5B3FF5] hover:text-[#4a32cc] hover:underline underline-offset-2 self-start sm:self-auto cursor-pointer"
                >
                  Editar motivo o fechas
                </button>
              </div>

              {/* Dropzone de Evidencias */}
              <EvidenceDropzone
                files={selectedFiles}
                onFilesChange={setSelectedFiles}
                maxFiles={5}
                maxSizeMB={10}
              />

              {/* Botones de Navegación Final */}
              <div className="pt-4 border-t border-slate-100 flex flex-col-reverse sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs sm:text-sm border border-slate-200 transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <ArrowLeft className="size-4" />
                  <span>Volver al Paso 1</span>
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full sm:w-auto px-7 py-3 rounded-xl bg-[#5B3FF5] hover:bg-[#4a32cc] text-white font-bold text-xs sm:text-sm transition-all shadow-lg shadow-[#5B3FF5]/30 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Radicando solicitud...</span>
                    </>
                  ) : (
                    <>
                      <Send className="size-4" />
                      <span>Finalizar y Radicar Justificación</span>
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </form>
    </div>
  );
}
