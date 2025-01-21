# Whisper-Timestamp-to-SRT

### Bu uygulama nedir, ne işe yarar?
Bu araç, [Hugging Face Space](https://huggingface.co/spaces/sanchit-gandhi/whisper-jax) gibi uygulamalar tarafından oluşturulan zaman damgalı altyazıları yaygın olarak kullanılan SRT formatına dönüştürmek için tasarlanmıştır. Program kendi başına altyazı oluşturmaz, sadece Whisper-JAX ve benzer formattaki çıktıları SRT formatına dönüştürür. VTT veya diğer formatları SRT'ye dönüştürmez (bu özellikler gelecek güncellemelerde eklenebilir).

### Özellikler
- Kolay kullanım arayüzü
- Her cihazla uyumluluk
- Çoklu çalışma desteği
- Hata kontrol mekanizması
- Açık kaynak kodlu

Arayüz görünümü:

![Uygulama Arayüzü](images/1.png)
![Örnek Kullanım](images/2.png)
![Sonuç Ekranı](images/3.png)

## Kurulum ve Gereksinimler

**NOT:** Python veya pip komutları çalışmazsa, python3 veya pip3 olarak deneyiniz.

### Windows için Kurulum:
1. **Python 3.x**
   - En son kararlı sürümü [Python'un resmi sitesinden](https://www.python.org/downloads/) indirebilirsiniz
   - Kurulum sırasında "Add Python to PATH" seçeneğini işaretlemeyi unutmayın

2. **PyQt5 Kurulumu**
   ```bash
   pip install PyQt5
   ```

3. Uygulamayı çalıştırmak için terminal üzerinden dosyanın bulunduğu dizine gidip aşağıdaki komutu çalıştırın:
   ```bash
   python app.py
   ```

### macOS için Kurulum:
1. **Python 3.x**
   - Homebrew ile kurulum:
   ```bash
   brew install python3
   ```
   - Veya [Python'un resmi sitesinden](https://www.python.org/downloads/) macOS için olan kurulum dosyasını indirin

2. **PyQt5 Kurulumu**
   ```bash
   pip3 install PyQt5
   ```

3. Uygulamayı çalıştırmak için terminal üzerinden dosyanın bulunduğu dizine gidip aşağıdaki komutu çalıştırın:
   ```bash
   python3 app.py
   ```

### Linux için Kurulum:
1. **Python 3.x**
   - Ubuntu/Debian için:
   ```bash
   sudo apt-get update
   sudo apt-get install python3
   ```
   - Fedora için:
   ```bash
   sudo dnf install python3
    ```

2. **PyQt5 Kurulumu**
   - Ubuntu/Debian için:
   ```bash
   sudo apt-get install python3-pyqt5
   ```
   - Veya pip ile kurulum:
   ```bash
   pip3 install PyQt5
   ```

3. Uygulamayı çalıştırmak için terminal üzerinden dosyanın bulunduğu dizine gidip aşağıdaki komutu çalıştırın:
   ```bash
   python3 app.py
   ```