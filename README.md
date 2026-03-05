# 📍 City locator

**City locator** is a premium, lightweight city guide designed for newcomers to navigate urban environments with ease. It provides refined recommendations for essential services like restaurants, hospitals, ATMs, and transit hubs—all within a stunning, Dribbble-inspired interface.

Built with performance and privacy in mind, **City locator** uses 100% free OpenStreetMap data, requiring no API keys or complex setups.

---

## ✨ Features

- 🎨 **Dribbble-Inspired UI:** A clean, modern "floating card" interface with soft shadows and premium typography.
- ⚡ **Zero-Configuration Setup:** No Google API keys or credit cards required. Just clone and run.
- 🤖 **ML-Ranking Engine:** Intelligently sorts places based on proximity, budget compatibility, and popularity.
- 🌆 **Multi-City Support:** Seamlessly switch between Nashik, Pune, Mumbai, and Thane.
- 📱 **Interactive Map:** High-performance mapping using Leaflet.js and CartoDB.
- 🛠️ **Custom Components:** Hand-crafted animated dropdowns and sliding detail overlays for an immersive experience.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- [Optional] Virtual matching environment

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/city-locator.git
   cd city-locator
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application:**
   ```bash
   python app.py
   ```

The app will be live at `http://127.0.0.1:5000`.

---

## 🛠️ Architecture

- **Backend:** Flask (Python)
- **Frontend:** Vanilla JS, HTML5, CSS3 (No bulky frameworks)
- **Data Source:** OpenStreetMap (Overpass & Nominatim APIs)
- **Maps:** Leaflet.js + CartoDB Positron

---

## 📜 Project Report

For a deep dive into the engineering decisions, scoring logic, and technical trade-offs, refer to the [Detailed Project Report](./project_report.md).

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
