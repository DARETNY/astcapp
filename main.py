import io
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import streamlit as st


def find_astcenc_path():
    system = platform.system()
    executable_name = "astcenc.exe" if system == "Windows" else "astcenc"

    search_paths = [
        os.path.join(os.getcwd(), executable_name),
        os.path.join(os.getcwd(), "xc", executable_name)
    ]

    for path in search_paths:
        if os.path.exists(path):
            if system != "Windows" and not os.access(path, os.X_OK):
                try:
                    os.chmod(path, os.stat(path).st_mode | 0o100)
                    if not os.access(path, os.X_OK):
                        pass
                except Exception:
                    pass
            return os.path.abspath(path)

    system_path = shutil.which(executable_name)
    if system_path:
        return system_path

    return ""


def create_zip_in_memory(files_to_zip):
    """Verilen dosya yollarının listesini alıp bellekte bir zip arşivi oluşturur."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in files_to_zip:
            zip_file.write(file_path, arcname=Path(file_path).name)
    return zip_buffer.getvalue()


def run_conversion(input_path, output_path, settings):
    """Verilen ayarlarla astcenc komutunu çalıştırır ve sonucu döndürür."""
    command = [
        settings["astcenc_path"],
        settings["color_profile"],
        str(input_path),
        str(output_path),
        settings["block_size"],
        settings["quality_key"]
    ]
    if settings["y_flip"]:
        command.append("-yflip")

    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result, command
    except FileNotFoundError:
        st.error(f"**KRİTİK HATA:** `astcenc` programı çalıştırılamadı. Dosya '{settings['astcenc_path']}' konumunda bulunamadı.")
        return None, command
    except OSError as e:
        if e.errno == 8:  # Exec format error
            st.error("**UYUMLULUK HATASI:** `astcenc` bu işlemci mimarisiyle uyumlu değil.")
        else:
            st.error(f"**İŞLETİM SİSTEMİ HATASI:** {e}")
        return None, command
    except Exception as e:
        st.error(f"**BEKLENMEDİK HATA:** {e}")
        return None, command


def display_result(original_file_path, original_filename, output_path, result, command):
    """Dönüştürme sonucunu arayüzde gösterir."""
    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(str(original_file_path), caption=f"Orijinal: {original_filename}", width=200)

    with col2:
        if result.returncode == 0:
            st.success(f"**`{original_filename}` başarıyla dönüştürüldü.**")

            output_filename = Path(output_path).name
            with open(output_path, "rb") as f:
                file_bytes = f.read()

            st.download_button(
                label=f"📥 `{output_filename}` İndir",
                data=file_bytes,
                file_name=output_filename,
                mime="application/octet-stream",
                key=f"dl_{original_filename}"
            )
            with st.expander("Çalıştırılan Komut"):
                st.code(' '.join(command), language="bash")
        else:
            st.error(f"**`{original_filename}` dönüştürülürken hata oluştu!**")
            with st.expander("Hata Detayları"):
                st.code(result.stderr or "Hata mesajı alınamadı.", language="bash")

    st.divider()


# --- STREAMLIT ARAYÜZÜ ---

st.set_page_config(page_title="ASTC Dönüştürücü", layout="wide")
st.title("🖼️ PNG'den ASTC'ye Dönüştürücü")
st.markdown("`.png` dosyalarınızı `.astc` formatına dönüştürmek için dosya yükleyin veya klasör yolu belirtin.")

# --- HATA AYIKLAMA BÖLÜMÜ ---
with st.expander("Hata Ayıklama Bilgileri"):
    try:
        sys_platform = platform.system()
        machine_arch = platform.machine()

        st.write(f"**İşletim Sistemi:** `{sys_platform}`")
        st.write(f"**Mimari (CPU):** `{machine_arch}`")

        cwd = os.getcwd()
        st.write(f"**Çalışma Dizini:** `{cwd}`")
        st.write("**Ana Dizin İçeriği:**")
        st.code('\n'.join(os.listdir(cwd)))

        bin_path = os.path.join(cwd, "bin")
        if os.path.exists(bin_path):
            st.write("**'bin' Klasörü İçeriği:**")
            st.code('\n'.join(os.listdir(bin_path)))
    except Exception as e:
        st.error(f"Hata ayıklama bilgileri alınırken hata: {e}")

st.divider()

# --- BÖLÜM 0: astcenc YOLU ---
st.subheader("⚙️ `astcenc` Programının Konumu")

auto_detected_path = find_astcenc_path()

ASTCENC_PATH = st.text_input(
    label="Kullanılacak `astcenc` yolu:",
    value=auto_detected_path,
    help="Doğru yolu kontrol edin."
)

if not ASTCENC_PATH or not os.path.exists(ASTCENC_PATH):
    st.error("Geçerli bir `astcenc` dosyası bulunamadı.")
    st.stop()
else:
    st.success(f"`astcenc` aracı bulundu: `{ASTCENC_PATH}`")

with st.sidebar:
    st.header("Dönüştürme Ayarları")
    block_sizes = ["4x4", "5x4", "5x5", "6x5", "6x6", "8x5", "8x6", "8x8", "10x5", "10x6", "10x8", "10x10", "12x10",
                   "12x12"]
    block_size_index = block_sizes.index("8x8") if "8x8" in block_sizes else 0
    quality_presets = {"-veryfast": "Çok Hızlı", "-fast": "Hızlı", "-medium": "Orta", "-thorough": "Detaylı",
                       "-exhaustive": "Kapsamlı"}
    quality_keys = list(quality_presets.keys())
    quality_index = quality_keys.index("-medium")
    conversion_settings = {
        "block_size": st.selectbox("Blok Boyutu", options=block_sizes, index=block_size_index),
        "quality_key": st.selectbox("Kalite",
                                    options=quality_keys,
                                    format_func=lambda x: quality_presets[x],
                                    index=quality_index),
        "y_flip": st.checkbox("Y-Ekseninde Ters Çevir (-yflip)", value=True),
        "color_profile": st.selectbox("Renk Profili", options=["-cl", "-cs", "-cr"], index=0),
        "astcenc_path": ASTCENC_PATH
    }

TEMP_DIR = "temp_conversion_files"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


def process_files(file_list, from_folder=False):
    """Dosya yükleme ile gelen dosyaları işler (indirilebilir)."""
    st.info(f"{len(file_list)} dosya işleniyor...")

    zip_button_placeholder = st.empty()
    successful_conversions = []
    results_container = st.container()

    for item in file_list:
        if from_folder:
            input_path = item
            original_filename = input_path.name
        else:
            input_path = Path(TEMP_DIR) / item.name
            original_filename = item.name
            with open(input_path, "wb") as f:
                f.write(item.getbuffer())

        output_path = Path(TEMP_DIR) / input_path.with_suffix(".astc").name

        result, command = run_conversion(input_path, output_path, conversion_settings)

        if result is None:
            st.warning("Kritik hata nedeniyle durdu.")
            break

        if result.returncode == 0:
            successful_conversions.append(output_path)

        with results_container:
            display_result(input_path, original_filename, output_path, result, command)

    if len(successful_conversions) > 1:
        zip_bytes = create_zip_in_memory(successful_conversions)
        zip_button_placeholder.download_button(
            label="📦 Tümünü .zip indir",
            data=zip_bytes,
            file_name="converted_astc_files.zip",
            mime="application/zip",
            use_container_width=True,
            key="download_all_zip"
        )


def process_folder(folder_path: Path):
    """Belirtilen klasördeki PNG'leri dönüştürür, aynı yerde .astc üretir (duplicateler atlanır)."""
    png_files = list(folder_path.rglob("*.png"))
    if not png_files:
        st.warning("Hiç `.png` bulunamadı.")
        return

    st.info(f"{len(png_files)} PNG bulundu, dönüştürme başlatılıyor...")

    for input_path in png_files:
        output_path = input_path.with_suffix(".astc")

        if output_path.exists():
            st.write(f"⚠️ {output_path} zaten mevcut, atlanıyor.")
            continue

        result, command = run_conversion(input_path, output_path, conversion_settings)

        if result is None:
            st.error(f"{input_path} dönüştürülemedi (kritik hata).")
            break

        if result.returncode == 0:
            st.success(f"✅ {input_path} → {output_path}")
        else:
            st.error(f"❌ {input_path} hata verdi.")
            with st.expander("Hata Detayı"):
                st.code(result.stderr or "Hata mesajı yok", language="bash")


# --- BÖLÜM 1: DOSYA YÜKLEME ---
st.subheader("1. Dosya Yükleyerek Dönüştür")
uploaded_files = st.file_uploader("PNG yükleyin", type="png", accept_multiple_files=True)
if uploaded_files:
    process_files(uploaded_files, from_folder=False)

st.divider()

# --- BÖLÜM 2: KLASÖR YOLU ---
st.subheader("2. Klasör Yolu Belirterek Dönüştür")
folder_path_str = st.text_input("Klasör yolu girin:", placeholder="Örn: C:\\Users\\profile\\Resimler")
if st.button("Klasördeki PNG'leri İşle"):
    if folder_path_str and os.path.isdir(folder_path_str):
        folder_path = Path(folder_path_str)
        process_folder(folder_path)
    else:
        st.error("Geçerli bir klasör yolu girin.")

if __name__ == '__main__':
    st.write("Uygulama çalışıyor ✅")
    st.stop()
