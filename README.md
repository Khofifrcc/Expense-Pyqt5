# 💸 Quick Expense Tracker

## 📌 Proje Amacı

Quick Expense Tracker, kullanıcıların günlük gelir ve gider işlemlerini hızlı, pratik ve kullanıcı dostu bir şekilde kaydedebileceği bir masaüstü uygulamasıdır.

Bu proje yalnızca veri kaydetmekle kalmaz, aynı zamanda kullanıcıya finansal durumunu analiz etme, harcama alışkanlıklarını anlama ve daha bilinçli bütçe yönetimi yapma imkanı sunar.

---

## 🚀 Proje Açıklaması

Quick Expense Tracker, PyQt5 kullanılarak geliştirilmiş bir finans takip uygulamasıdır.

Kullanıcılar:

* Manuel olarak işlem ekleyebilir
* Fiş fotoğraflarını tarayarak otomatik veri elde edebilir (OCR)
* Sesli komut ile hızlı giriş yapabilir
* İşlemleri filtreleyebilir, düzenleyebilir ve silebilir
* AI destekli öneriler alabilir

---

## 🧠 Özellikler

### 📊 Dashboard

* Toplam gelir, gider ve bakiye görüntüleme
* Grafiklerle finansal durum analizi
* Son işlemler listesi

### ✍️ Manual Input

* Gelir / gider ekleme
* Sesli veri girişi (voice input)
* Otomatik form doldurma

### 📷 Scan Receipt (OCR)

* Fiş fotoğrafı yükleme
* Kamera ile anlık tarama
* EasyOCR ile metin okuma
* Store name, tarih ve toplam tutar extraction

### 📋 Transactions

* Tüm işlemleri listeleme
* Arama ve filtreleme
* Edit ve delete işlemleri

### 🤖 AI Features

* Otomatik kategori tahmini (rule-based)
* Finansal analiz ve öneriler
* AI Advisor (chat tabanlı sistem)

---

## 🛠 Kullanılan Teknolojiler

* Python
* PyQt5
* SQLite
* OpenCV
* EasyOCR
* SpeechRecognition
* Matplotlib (ChartCanvas)

---

## 📂 Proje Yapısı

```bash
VizeExpense/
│── main.py
│── database.py
│── services/
│── ui/
│   ├── main_window.py
│   ├── pages.py
│   ├── components.py
│── receipts.db
│── assets/
```

---

## ⚙️ Kurulum

### 1. Depoyu klonlayın

```bash
git clone https://github.com/username/quick-expense-tracker.git
cd quick-expense-tracker
```

### 2. Gerekli paketleri yükleyin

```bash
pip install -r requirements.txt
```

### 3. Uygulamayı çalıştırın

```bash
python main.py
```

---

## 🖥 Demo

Uygulama masaüstü tabanlıdır. Çalıştırıldığında tüm modüller aktif olarak kullanılabilir.

---

## 📌 Notlar

* OCR işlemleri CPU üzerinde çalışmaktadır (GPU ile daha hızlı olabilir)
* Sesli veri girişi için mikrofon erişimi gereklidir
* İlk çalıştırmada veritabanı otomatik oluşturulur

---

## 👥 Proje Ekibi

* **Khofif Rohma Cahyani**
* Muhammad Dhafin Faza
* Andhika Surya Maulana

---

## 📎 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
