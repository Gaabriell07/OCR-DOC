from pathlib import Path
import streamlit as st

from ocr_engine import (
    ConversionError, Job, cleanup_old_jobs, export_docx, ocr_status,
    prepare_job, preview, update_regions,
)

st.set_page_config(page_title="OCR DOC · Escaneos a Word", page_icon="📄", layout="wide")


def clear_download():
    st.session_state.pop("download", None)


def save_text():
    if "job" not in st.session_state or "editor_index" not in st.session_state:
        return
    job = Job(st.session_state.job)
    index = st.session_state.editor_index
    page = job.page(index)
    page["text"] = st.session_state.editor
    job.save_page(index, page)
    clear_download()


def change_page():
    save_text()
    st.session_state.pop("editor_index", None)


st.markdown("""<style>
.block-container {max-width:1150px; padding-top:2.2rem; padding-bottom:2rem}
h1 {font-size:2rem !important; letter-spacing:-.04em;}
.eyebrow {font-size:.8rem; font-weight:650; letter-spacing:.13em; color:#17654f}
.steps {color:#52616c; border-top:1px solid #e1e7eb; border-bottom:1px solid #e1e7eb;
padding:14px 0; margin:20px 0 24px; font-size:.95rem}
button:focus-visible {outline:3px solid #17654f !important; outline-offset:3px}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">OCR DOC · EN TU COMPUTADORA</div>', unsafe_allow_html=True)
st.title("De escaneo a Word")
st.write("Recupera el texto de tus documentos y continúa trabajando en Word.")
st.markdown('<div class="steps">1. Carga el documento　 →　 2. Revisa el resultado　 →　 3. Descarga el Word</div>', unsafe_allow_html=True)

if "initialized" not in st.session_state:
    cleanup_old_jobs()
    st.session_state.initialized = True

if "job" not in st.session_state:
    st.subheader("Carga tu escaneo")
    st.caption("PDF, JPG, PNG o TIFF · hasta 50 MB y 150 páginas por archivo")
    uploaded = st.file_uploader("Arrastra el documento aquí o selecciónalo", type=["pdf", "jpg", "jpeg", "png", "tif", "tiff"], key=f"upload-{st.session_state.get('upload_version', 0)}")
    with st.expander("Opciones de lectura"):
        quality = st.radio("Calidad", ["Equilibrada", "Más detalle"], horizontal=True,
                           help="Equilibrada reduce el tamaño de las páginas. Más detalle ayuda con letras pequeñas.")
        st.caption("Fotos: procura que la hoja esté recta, bien iluminada y completa.")
    if "ocr_ready" not in st.session_state:
        st.session_state.ocr_ready = ocr_status()
    ready, message = st.session_state.ocr_ready
    if not ready:
        st.warning(message + " Los PDF que ya contienen texto se pueden convertir sin OCR.")
        if st.button("Volver a comprobar OCR"):
            st.session_state.pop("ocr_ready", None)
            st.rerun()
    if st.button("Convertir documento", type="primary", disabled=uploaded is None):
        job = Job.create()
        bar = st.progress(0, text="Preparando documento…")
        try:
            prepare_job(job, uploaded, uploaded.name, dpi=180 if quality == "Equilibrada" else 220,
                        progress=lambda done, total: bar.progress(done / total, text=f"Leyendo página {done} de {total}…"))
            st.session_state.job = str(job.directory)
            st.session_state.page_number = 1
            st.session_state.upload_version = st.session_state.get("upload_version", 0) + 1
            # Release Streamlit's upload widget on the next run.
            st.rerun()
        except ConversionError as exc:
            job.close()
            bar.empty()
            st.error(str(exc))
        except Exception:
            job.close()
            bar.empty()
            st.error("No se pudo convertir el documento. Prueba con un PDF o una imagen más pequeña y válida.")
    st.caption("Procesamiento local. No se envían tus documentos a un servicio de conversión.")
    st.stop()

job = Job(st.session_state.job)
meta = job.meta()
st.subheader("Revisa tu documento")
st.caption(f"{meta['name']} · {meta['count']} página(s). Los cambios de texto se guardan al salir del campo.")
index = int(st.number_input("Página", min_value=1, max_value=meta["count"], step=1,
                            key="page_number", on_change=change_page)) - 1
page = job.page(index)
if st.session_state.get("editor_index") != index:
    st.session_state.editor_index = index
    st.session_state.editor = page["text"]

left, right = st.columns([1, 1], gap="large")
with left:
    st.markdown("**Original**")
    with st.expander("Conservar logo, sello o firma / girar la página"):
        st.caption("Selecciona una franja superior o inferior. Se conservará completa como imagen y su texto dejará de ser editable. Las líneas verdes muestran los límites.")
        top = st.slider("Franja superior (%)", 0, 45, page["top"], key=f"top-{index}")
        bottom = st.slider("Franja inferior (%)", 0, 45, page["bottom"], key=f"bottom-{index}")
        rotation = st.selectbox("Giro horario", [0, 90, 180, 270], index=page["rotation"] // 90,
                                format_func=lambda value: f"{value}°", key=f"rotation-{index}")
        st.caption("Aplicar vuelve a reconocer esta página y reemplaza sus correcciones de texto. Después podrás corregirla otra vez.")
        if st.button("Aplicar selección y volver a leer", key=f"apply-{index}"):
            try:
                with st.spinner("Leyendo esta página…"):
                    update_regions(job, index, top, bottom, rotation)
                st.session_state.pop("editor_index", None)
                clear_download()
                st.rerun()
            except ConversionError as exc:
                st.error(str(exc))
    image = preview(job, index, top, bottom)
    st.image(image, caption="Original · las franjas se conservan solo al pulsar Aplicar", width="stretch")
    image.close()
with right:
    st.markdown("**Texto editable**")
    st.text_area("Corrige aquí el texto de esta página", key="editor", height=620, on_change=save_text)
    if not page["text"].strip():
        st.warning("No se encontró texto. Comprueba la orientación y vuelve a leer la página.")
    st.caption("Comprueba nombres, fechas y montos con el original. El formato y la ubicación de las imágenes en Word son aproximados.")

st.divider()
if st.button("Preparar Word", type="primary"):
    save_text()
    try:
        with st.spinner("Preparando tu Word…"):
            result = export_docx(job)
        st.session_state.download = str(result)
    except Exception:
        st.error("No se pudo generar el Word. Comprueba que haya espacio libre en tu equipo.")

if "download" in st.session_state:
    st.success("Tu documento está listo. Descárgalo y ábrelo en Word.")
    with Path(st.session_state.download).open("rb") as output:
        st.download_button("Descargar Word (.docx)", data=output, file_name=f"{meta['name']}-editable.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with st.expander("Terminar y cargar otro documento"):
    st.caption("Descarga primero el Word. Al terminar se eliminarán los archivos temporales y las correcciones de esta sesión.")
    if st.button("Eliminar esta sesión y empezar otro documento"):
        job.close()
        version = st.session_state.get("upload_version", 0) + 1
        st.session_state.clear()
        st.session_state.upload_version = version
        st.rerun()
