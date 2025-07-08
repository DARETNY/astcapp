import io
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import streamlit as st


def find_astcenc_path():
    """
    astcenc'i arar, bulur ve çalıştırılabilir olduğundan emin olur.
    Değilse, izinleri ayarlamaya çalışır.
    """
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
    """
    Verilen dosya yollarının listesini alıp bellekte bir zip arşivi oluşturur.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in files_to_zip:
            zip_file.write(file_path, arcname=Path(file_path).name)
    return zip_buffer.getvalue()


def run_conversion(input_path, output_path, settings):
    """
    Verilen ayarlarla astcenc komutunu çalıştırır ve sonucu döndürür.
    """
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
            st.error(f"**UYUMLULUK HATASI (Exec format error):** `astcenc` programı bu sunucunun işlemci mimarisiyle uyumlu değil. Lütfen 'Hata Ayıklama Bilgileri' bölümündeki talimatları izleyerek doğru dosyayı indirin.")
        else:
            st.error(f"**BEKLENMEDİK İŞLETİM SİSTEMİ HATASI:** `astcenc` çalıştırılırken bir hata oluştu: {e}")
        return None, command
    except Exception as e:
        st.error(f"**BEKLENMEDİK HATA:** `astcenc` çalıştırılırken bir hata oluştu: {e}")
        return None, command


def display_result(original_file_path, original_filename, output_path, result, command):
    """
    Dönüştürme sonucunu arayüzde gösterir.
    """
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
            with st.expander("Çalıştırılan Komutun Detayları"):
                st.code(' '.join(command), language="bash")
        else:
            st.error(f"**`{original_filename}` dönüştürülürken bir hata oluştu!**")
            with st.expander("Hata Detayları"):
                st.code(result.stderr or "Hata mesajı alınamadı.", language="bash")

    st.divider()


# --- STREAMLIT ARAYÜZÜ ---

st.set_page_config(page_title="ASTC Dönüştürücü", layout="wide")
st.title("🖼️ PNG'den ASTC'ye Dönüştürücü")
st.markdown("`.png` dosyalarınızı `.astc` formatına dönüştürmek için dosya yükleyin veya klasör yolu belirtin.")

# --- HATA AYIKLAMA BÖLÜMÜ ---
with st.expander("Yardımcı Hata Ayıklama Bilgileri (Yol ve Uyumluluk Sorunları İçin)"):
    try:
        # Sistem bilgilerini al
        sys_platform = platform.system()
        machine_arch = platform.machine()

        st.write(f"**Sunucu İşletim Sistemi:** `{sys_platform}`")
        st.write(f"**Sunucu Mimarisi (CPU Tipi):** `{machine_arch}`")

        # Streamlit Cloud için özel talimat
        if sys_platform == "Linux" and machine_arch == "x86_64":
            st.info(
                "**ÖNEMLİ BİLGİ:** Bu sunucu Linux (x86_64) üzerinde çalışıyor. "
                "`astcenc` programının doğru sürümünü kullandığınızdan emin olun.\n\n"
                "1. [ARM ASTC Encoder Releases](https://github.com/ARM-software/astc-encoder/releases) sayfasına "
                "gidin.\n"
                "2. `astcenc-x.x.x-linux-x64-sse4.1.zip` gibi **linux-x64** içeren dosyayı indirin.\n"
                "3. İndirdiğiniz zip dosyasını açın ve içindeki `bin` klasöründe bulunan `astcenc` dosyasını "
                "projenizin `bin` klasörüne yükleyin."
            )

        cwd = os.getcwd()
        st.write(f"**Mevcut Çalışma Dizini:** `{cwd}`")
        st.write("**Ana Dizin İçeriği:**")
        st.code('\n'.join(os.listdir(cwd)))

        bin_path = os.path.join(cwd, "bin")
        if os.path.exists(bin_path):
            st.write("**'bin' Klasörü İçeriği:**")
            st.code('\n'.join(os.listdir(bin_path)))
    except Exception as e:
        st.error(f"Hata ayıklama bilgileri alınırken bir hata oluştu: {e}")

st.divider()

# --- BÖLÜM 0: astcenc YOLU AYARI ---
st.subheader("⚙️ `astcenc` Programının Konumu")

auto_detected_path = find_astcenc_path()

ASTCENC_PATH = st.text_input(
    label="Kullanılacak `astcenc` yolunu onaylayın veya düzenleyin:",
    value=auto_detected_path,
    help="Uygulamanın kullanacağı `astcenc` programının tam yolu. Yukarıdaki 'Hata Ayıklama Bilgileri' bölümünden doğru yolu bulabilirsiniz."
)

if not ASTCENC_PATH or not os.path.exists(ASTCENC_PATH):
    st.error(
        "Yukarıda belirtilen yolda geçerli bir `astcenc` dosyası bulunamadı. Lütfen yolu kontrol edin veya programı projenize (örneğin 'bin' klasörüne) eklediğinizden emin olun.")
    st.stop()
else:
    st.success(f"`astcenc` aracı şu yolda kullanılacak: `{ASTCENC_PATH}`")

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
        "quality_key": st.selectbox("Kalite Profili",
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
    """Dosya listesini işler, dönüştürür ve sonuçları gösterir."""
    st.info(f"{len(file_list)} adet dosya işleniyor...")

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
            st.warning("Kritik bir hata nedeniyle işlemler durduruldu.")
            break

        if result.returncode == 0:
            successful_conversions.append(output_path)

        with results_container:
            display_result(input_path, original_filename, output_path, result, command)

    if len(successful_conversions) > 1:
        zip_bytes = create_zip_in_memory(successful_conversions)
        zip_button_placeholder.download_button(
            label="📦 Tümünü .zip Olarak İndir",
            data=zip_bytes,
            file_name="converted_astc_files.zip",
            mime="application/zip",
            use_container_width=True,
            key="download_all_zip"
        )


# --- BÖLÜM 1: DOSYA YÜKLEME ---
st.subheader("1. Dosyaları Yükleyerek Dönüştür")
uploaded_files = st.file_uploader(
    "Dönüştürmek istediğiniz PNG dosyalarını buraya sürükleyin veya seçin",
    type="png",
    accept_multiple_files=True
)
if uploaded_files:
    process_files(uploaded_files, from_folder=False)

st.divider()

# --- BÖLÜM 2: KLASÖR YOLU ---
st.subheader("2. Klasör Yolu Belirterek Dönüştür")
folder_path_str = st.text_input(
    "İşlem yapılacak klasörün yolunu yapıştırın:",
    placeholder="Örn: C:\\Users\\Kullanici\\Resimlerim"
)
if st.button("Klasördeki PNG'leri İşle"):
    if folder_path_str and os.path.isdir(folder_path_str):
        folder_path = Path(folder_path_str)
        png_files = list(folder_path.glob("**/*.png"))

        if not png_files:
            st.warning("Belirtilen klasörde ve alt klasörlerinde hiç `.png` dosyası bulunamadı.")
        else:
            process_files(png_files, from_folder=True)
    else:
        st.error("Lütfen geçerli bir klasör yolu girin.")
if __name__ == '__main__':
    st.write("Uygulama çalışıyor. Lütfen yukarıdaki bölümleri kullanarak dosyalarınızı dönüştürün.")
    st.stop()
