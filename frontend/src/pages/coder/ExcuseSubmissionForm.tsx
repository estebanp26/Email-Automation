import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
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
  RefreshCw,
  LogOut,
  Inbox,
  PlusCircle
} from 'lucide-react';
import { 
  excuseFormSchema, 
  type ExcuseFormData, 
  NOVELTY_TYPES, 
  type NoveltyTypeId 
} from '../../schemas/excuseValidationSchema';
import { EvidenceDropzone, type SelectedFile } from '../../components/coder/EvidenceDropzone';
import { getCoderSession } from '../../utils/coderSession';
import { saveNewCoderJustification } from '../../utils/coderJustifications';
import { useAuth } from '../../context/AuthContext';

export default function ExcuseSubmissionForm() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [submissionSuccess, setSubmissionSuccess] = useState<null | {
    radicadoId: string;
    submittedAt: string;
    data: ExcuseFormData;
    filesCount: number;
  }>(null);

  const session = useMemo(() => getCoderSession(), []);

  const initials = useMemo(() => {
    if (!session.name) return 'CO';
    const parts = session.name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }, [session.name]);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  // Configuración de React Hook Form + Zod con persistencia de campos no montados
  const {
    register,
    watch,
    setValue,
    getValues,
    formState: { errors },
    trigger,
  } = useForm<ExcuseFormData>({
    resolver: zodResolver(excuseFormSchema),
    mode: 'onChange',
    shouldUnregister: false,
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

  const isUploadingFiles = selectedFiles.some((f) => f.status === 'uploading');

  // Manejador de envío final simulado (preparado para backend y Supabase Storage)
  const onSubmitFinal = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    // Validar integridad de datos
    const valid = await trigger();
    if (!valid) {
      setCurrentStep(1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    if (isUploadingFiles) {
      return;
    }

    const data = getValues();
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
        attachments: selectedFiles.map((f) => ({
          file_id: f.id,
          filename: f.name,
          size_bytes: f.size,
          mime_type: f.type,
          legibility_status: f.legibility,
          legibility_reason: f.legibilityReason,
          // Estructura preparada para endpoints de carga o URLs prefirmadas de Supabase Storage
          storage_bucket: 'hse-evidences',
          storage_path: f.storagePath || `evidences/coder/${f.id}/${f.name}`,
          upload_status: f.status,
        })),
        submitted_at: new Date().toISOString(),
      };

      console.log('Payload estructurado preparado para Supabase Storage / Backend:', payloadReadyForBackend);

      // Persistir la justificación para el Coder en su historial
      saveNewCoderJustification(payloadReadyForBackend);

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
    }, 800);
  };

  const getNoveltyIcon = (id: NoveltyTypeId) => {
    switch (id) {
      case 'incapacidad_medica':
        return <Stethoscope className="size-4 text-[#20B486]" />;
      case 'calamidad_domestica':
        return <HeartHandshake className="size-4 text-[#F5B83D]" />;
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
        className="max-w-2xl mx-auto p-6 sm:p-8 rounded-3xl bg-white border border-[#E2E8F0] shadow-sm relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
          <Sparkles className="size-48 text-[#5B3FF5]" />
        </div>

        <div className="size-16 sm:size-20 rounded-2xl bg-[#20B486]/10 border border-[#20B486]/30 flex items-center justify-center text-[#20B486] mb-6 mx-auto shadow-md shadow-[#20B486]/10">
          <CheckCircle2 className="size-10 sm:size-12" />
        </div>

        <div className="text-center space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-[#20B486] font-mono">
            Reporte Radicado Exitosamente
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#111827]">
            ¡Tu justificación ha sido enviada!
          </h2>
          <p className="text-sm text-[#7C8499] max-w-md mx-auto">
            El equipo de <strong className="text-[#111827]">Habilidades para la Vida (HSE)</strong> revisará tu reporte y recibirás la notificación de respuesta en tu correo institucional.
          </p>
        </div>

        {/* Resumen del Radicado */}
        <div className="mt-8 p-6 rounded-2xl bg-gray-50/70 border border-[#E2E8F0] space-y-3.5 text-xs sm:text-sm">
          <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
            <span className="text-[#7C8499]">Número de Radicado:</span>
            <span className="font-mono font-bold text-[#5B3FF5] bg-[#F2F0FF] px-3 py-1 rounded-lg border border-[#5B3FF5]/30">
              {submissionSuccess.radicadoId}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Coder:</span>
            <span className="font-semibold text-[#111827]">{session.name} ({session.cedula})</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Tipo de Novedad:</span>
            <span className="font-medium text-[#111827] capitalize">
              {activeNoveltyInfo.label}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Periodo reportado:</span>
            <span className="font-medium text-[#111827]">
              {submissionSuccess.data.start_date} al {submissionSuccess.data.end_date}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[#7C8499]">Evidencias adjuntas:</span>
            <span className="font-semibold text-[#20B486]">
              {submissionSuccess.filesCount} soporte(s) registrado(s)
            </span>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[#E2E8F0] text-[11px] text-[#7C8499]">
            <span>Fecha y hora de registro:</span>
            <span className="font-mono">{submissionSuccess.submittedAt}</span>
          </div>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/coder/history')}
            className="w-full sm:flex-1 py-3.5 px-4 rounded-xl bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-95 text-white font-semibold text-sm transition-all shadow-[0_8px_20px_rgba(99,59,255,0.25)] flex items-center justify-center gap-2 cursor-pointer"
          >
            <span>Ver en Historial de Solicitudes</span>
            <ArrowRight className="size-4" />
          </button>

          <button
            type="button"
            onClick={() => {
              setSubmissionSuccess(null);
              setCurrentStep(1);
              setSelectedFiles([]);
            }}
            className="w-full sm:w-auto py-3.5 px-5 rounded-xl bg-white hover:bg-gray-50 text-[#111827] font-semibold text-sm border border-[#E2E8F0] transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-sm"
          >
            <RefreshCw className="size-4" />
            <span>Radicar otra</span>
          </button>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Banner de Bienvenida del Coder */}
      <div className="p-6 rounded-3xl bg-white border border-[#E2E8F0] shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#5B3FF5]">
              Portal del Coder · Reporte de Justificaciones
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[#111827] tracking-tight">
            Hola, {session.name.split(' ')[0]} 👋
          </h1>
          <p className="text-xs sm:text-sm text-[#7C8499] max-w-xl">
            Registra tu novedad de inasistencia o tardanza con los soportes requeridos para que el equipo HSE mantenga al día tu trazabilidad formativa.
          </p>
        </div>

        <div className="flex items-center gap-3 self-stretch sm:self-auto justify-between sm:justify-end">
          {/* Stepper Visual interactivo */}
          <div className="flex items-center gap-2 bg-[#F6F7FB] p-1.5 rounded-2xl border border-[#E2E8F0]">
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                currentStep === 1
                  ? 'bg-gradient-to-r from-[#5636F5] to-[#633BFF] text-white shadow-md shadow-[#5B3FF5]/30'
                  : 'text-[#7C8499] hover:text-[#111827]'
              }`}
            >
              <span className={`size-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                currentStep === 1 ? 'bg-white/20 text-white' : 'bg-white text-[#7C8499] border border-[#E2E8F0]'
              }`}>
                1
              </span>
              <span>1. Motivo</span>
            </button>

            <div className="h-4 w-px bg-[#CBD5E1]" />

            <button
              type="button"
              onClick={handleProceedToEvidence}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                currentStep === 2
                  ? 'bg-gradient-to-r from-[#5636F5] to-[#633BFF] text-white shadow-md shadow-[#5B3FF5]/30'
                  : 'text-[#7C8499] hover:text-[#111827]'
              }`}
            >
              <span className={`size-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                currentStep === 2 ? 'bg-white/20 text-white' : 'bg-white text-[#7C8499] border border-[#E2E8F0]'
              }`}>
                2
              </span>
              <span>2. Evidencias</span>
            </button>
          </div>

          {/* Avatar del Coder con menú desplegable */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="size-10 rounded-full bg-[#11132C] hover:ring-2 hover:ring-[#5B3FF5] transition-all flex items-center justify-center text-white font-bold text-sm select-none shadow-md shadow-[#11132C]/20 border border-white/10 cursor-pointer"
              title={`${session.name} · Clic para opciones`}
            >
              {initials}
            </button>

            {showProfileMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowProfileMenu(false)} 
                />
                <div className="absolute top-12 right-0 w-60 bg-white rounded-2xl shadow-2xl border border-gray-100 py-3 z-50 divide-y divide-gray-100">
                  <div className="px-4 py-2">
                    <p className="text-[10px] text-[#7C8499] uppercase font-bold tracking-wider">Coder Conectado</p>
                    <p className="text-sm font-bold text-[#111827] truncate mt-0.5">{session.name}</p>
                    <p className="text-xs text-[#7C8499] font-mono">CC: {session.cedula}</p>
                    <span className="inline-block mt-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#5B3FF5]/10 text-[#5B3FF5]">
                      {session.route || 'Ruta Web'}
                    </span>
                  </div>

                  <div className="py-1">
                    <button
                      type="button"
                      onClick={() => {
                        setShowProfileMenu(false);
                        navigate('/coder/history');
                      }}
                      className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer"
                    >
                      <Inbox size={16} className="text-[#5B3FF5]" />
                      <span>Historial de solicitudes</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowProfileMenu(false);
                        navigate('/coder/new-excuse');
                      }}
                      className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#111827] hover:bg-[#F6F7FB] flex items-center gap-3 transition-colors cursor-pointer font-medium"
                    >
                      <PlusCircle size={16} className="text-[#5B3FF5]" />
                      <span>Radicar Justificación</span>
                    </button>
                  </div>

                  <div className="pt-1">
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-xs sm:text-sm text-[#FF5C67] hover:bg-red-50 flex items-center gap-3 transition-colors cursor-pointer font-semibold"
                    >
                      <LogOut size={16} className="text-[#FF5C67]" />
                      <span>Cerrar sesión</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Contenedor del Formulario con transiciones */}
      <form onSubmit={onSubmitFinal} className="space-y-6">
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
              className="p-6 sm:p-8 rounded-3xl bg-white border border-[#E2E8F0] shadow-sm space-y-6"
            >
              <div className="border-b border-[#E2E8F0] pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-[#111827] flex items-center gap-2">
                    <FileText className="size-5 text-[#5B3FF5]" />
                    Paso 1: Detalle del Motivo de Inasistencia
                  </h2>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    Selecciona el tipo de novedad e indica las fechas exactas de la inasistencia.
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold text-[#5B3FF5] bg-[#F2F0FF] px-2.5 py-1 rounded-lg border border-[#5B3FF5]/20">
                  Paso 1 de 2
                </span>
              </div>

              {/* 1. Selector de Tipo de Novedad */}
              <div className="space-y-2.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-[#111827]">
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
                            ? 'bg-[#F2F0FF] border-[#5B3FF5] shadow-sm ring-2 ring-[#5B3FF5]/20'
                            : 'bg-white border-[#E2E8F0] hover:border-[#5B3FF5]/40 hover:bg-[#F6F7FB]'
                        }`}
                      >
                        <div className="flex items-center justify-between w-full mb-2">
                          <div className="flex items-center gap-2">
                            {getNoveltyIcon(type.id)}
                            <span className="text-xs font-bold text-[#111827]">
                              {type.label}
                            </span>
                          </div>
                          <span
                            className={`size-4 rounded-full border flex items-center justify-center ${
                              isSelected
                                ? 'border-[#5B3FF5] bg-[#5B3FF5]'
                                : 'border-[#CBD5E1] bg-white'
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
                className="p-4 rounded-2xl bg-[#F2F0FF] border border-[#5B3FF5]/20 flex items-start gap-3 text-xs"
              >
                <AlertTriangle className="size-4 shrink-0 text-[#5B3FF5] mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-bold text-[#5B3FF5] uppercase tracking-wide text-[10px]">
                    Criterio HSE para {activeNoveltyInfo.label}
                  </span>
                  <p className="text-[#17203A] leading-relaxed">
                    {activeNoveltyInfo.alert}
                  </p>
                </div>
              </motion.div>

              {/* 3. Fechas de Inicio y Fin */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#111827]">
                    Fecha de Inicio <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      {...register('start_date')}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-[#E2E8F0] text-[#111827] text-xs sm:text-sm focus:outline-none focus:border-[#5B3FF5] focus:ring-4 focus:ring-[#5B3FF5]/10 transition-all font-mono"
                    />
                  </div>
                  {errors.start_date && (
                    <p className="text-xs text-rose-500 font-medium">{errors.start_date.message}</p>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#111827]">
                    Fecha de Finalización <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="date"
                      {...register('end_date')}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-[#E2E8F0] text-[#111827] text-xs sm:text-sm focus:outline-none focus:border-[#5B3FF5] focus:ring-4 focus:ring-[#5B3FF5]/10 transition-all font-mono"
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
                  <label className="block text-xs font-bold uppercase tracking-wider text-[#111827]">
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
                  className="w-full p-3.5 rounded-2xl bg-white border border-[#E2E8F0] text-[#111827] text-xs sm:text-sm placeholder:text-[#A3AAC2] focus:outline-none focus:border-[#5B3FF5] focus:ring-4 focus:ring-[#5B3FF5]/10 transition-all resize-none leading-relaxed"
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
              <div className="p-4 rounded-2xl bg-[#F6F7FB] border border-[#E2E8F0] space-y-2">
                <label className="flex items-start gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    {...register('truth_declaration')}
                    className="size-4 rounded mt-0.5 accent-[#5B3FF5] cursor-pointer"
                  />
                  <span className="text-xs text-[#17203A] leading-relaxed">
                    <strong className="text-[#111827]">Declaración bajo gravedad de juramento:</strong> Declaro
                    que la información suministrada y los soportes adjuntos son verídicos, auténticos y corresponden a mi situación particular durante las fechas indicadas.
                  </span>
                </label>
                {errors.truth_declaration && (
                  <p className="text-xs text-rose-500 font-medium pl-7">
                    {errors.truth_declaration.message}
                  </p>
                )}
              </div>

              {/* 6. Botón Continuar con Evidencias en morado y blanco RIWI */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={handleProceedToEvidence}
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-95 text-white font-bold text-xs sm:text-sm transition-all shadow-[0_8px_20px_rgba(99,59,255,0.25)] flex items-center justify-center gap-2 cursor-pointer"
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
              className="p-6 sm:p-8 rounded-3xl bg-white border border-[#E2E8F0] shadow-sm space-y-6"
            >
              <div className="border-b border-[#E2E8F0] pb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-[#111827] flex items-center gap-2">
                    <ShieldCheck className="size-5 text-[#5B3FF5]" />
                    Paso 2: Adjuntar Soportes Probatorios
                  </h2>
                  <p className="text-xs text-[#7C8499] mt-0.5">
                    Adjunta los certificados médicos, capturas o radicados que respaldan tu justificación.
                  </p>
                </div>
                <span className="text-xs font-mono font-semibold text-[#5B3FF5] bg-[#F2F0FF] px-2.5 py-1 rounded-lg border border-[#5B3FF5]/20">
                  Paso 2 de 2
                </span>
              </div>

              {/* Resumen compacto del Paso 1 */}
              <div className="p-4 rounded-2xl bg-gray-50/70 border border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-white border border-[#E2E8F0] flex items-center justify-center shadow-sm">
                    {getNoveltyIcon(selectedType)}
                  </div>
                  <div>
                    <p className="font-bold text-[#111827]">{activeNoveltyInfo.label}</p>
                    <p className="text-[#7C8499] font-mono text-[11px]">
                      Periodo: {watch('start_date')} al {watch('end_date')}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="text-xs font-semibold text-[#5B3FF5] hover:text-[#4A2FE0] hover:underline underline-offset-2 self-start sm:self-auto cursor-pointer"
                >
                  Editar motivo o fechas
                </button>
              </div>

              {/* Dropzone de Evidencias (FE-02: react-dropzone, Magic Numbers, max 3 archivos) */}
              <EvidenceDropzone
                files={selectedFiles}
                onFilesChange={setSelectedFiles}
                maxFiles={3}
                maxSizeMB={10}
              />

              {/* Botones de Navegación Final */}
              <div className="pt-4 border-t border-[#E2E8F0] flex flex-col-reverse sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="w-full sm:w-auto px-5 py-3 rounded-xl bg-white hover:bg-[#F2F0FF] text-[#111827] hover:text-[#5B3FF5] font-semibold text-xs sm:text-sm border border-[#E2E8F0] hover:border-[#5B3FF5]/40 transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
                >
                  <ArrowLeft className="size-4" />
                  <span>Volver al Paso 1</span>
                </button>

                <button
                  type="submit"
                  disabled={isSubmitting || isUploadingFiles}
                  className="w-full sm:w-auto px-7 py-3 rounded-xl bg-gradient-to-r from-[#5636F5] to-[#633BFF] hover:opacity-95 text-white font-bold text-xs sm:text-sm transition-all shadow-[0_8px_20px_rgba(99,59,255,0.25)] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Enviando justificación...</span>
                    </>
                  ) : isUploadingFiles ? (
                    <>
                      <div className="size-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Procesando evidencias...</span>
                    </>
                  ) : (
                    <>
                      <Send className="size-4" />
                      <span>Enviar Justificación</span>
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
