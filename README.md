# ✈️🌍 Yatra Sathi - AI Travel Companion 🏨🗺️

**Yatra Sathi** (meaning *Travel Companion* in Sanskrit/Hindi) is a stateful, AI-powered travel assistant chatbot. It is designed to take the friction out of travel planning by consolidating flights searches, hotel listings, and email automation into a single, interactive conversational experience.

Powered by **LangGraph** and **Google Gemini** (`gemini-3.5-flash`), Yatra Sathi offers a secure, human-in-the-loop automated itinerary generation loop.

![Yatra Sathi Application UI](images/yatra_sathi_ui.png)

---

## 💡 What Problem Does it Solve?
Planning a trip usually requires context-switching across dozens of tabs: flight comparison engines, hotel booking websites, calendars, and notes.

Yatra Sathi solves this by:
1. **Unified Conversational Agent**: You plan your entire trip (flights and hotels) inside a single, intuitive chat window.
2. **Keyless local setup**: No need to fiddle with `.env` files to get started. You can configure all API keys directly from the **sidebar UI**.
3. **Structured Live Results**: Queries Google Flights and Google Hotels in real-time (via SerpAPI) to return precise airline names, hotel star ratings, prices, links, and branding logos.
4. **Human-in-the-Loop Emailing**: Integrates with SendGrid to format and mail the itinerary straight to your inbox. The agent pauses before sending, allowing you to review the draft layout in the browser and authorize the dispatch.
5. **Rate & Quota Efficiency**: Uses cost-effective, high-speed `gemini-3.5-flash` models to execute reasoning and formatting, bypassing the strict rate limits of Pro models.

---

## 🛠️ Getting Started

### Prerequisites
Make sure you have Python 3.12+ and [Poetry](https://python-poetry.org/) installed on your machine.

### Installation
1. Clone this repository to your local machine:
   ```bash
   git clone <your-repository-url>
   cd yatra-sathi
   ```
2. Install the package dependencies using Poetry:
   ```bash
   poetry install
   ```

---

## 🚀 How to Run the App

1. Launch the Streamlit local web server:
   ```bash
   poetry run streamlit run app.py
   ```
2. Open your browser and navigate to the address shown (usually `http://localhost:8501` or `http://localhost:8502`).
3. **Enter your API Credentials in the Sidebar**:
   To activate search and email features, input all three mandatory API keys in the sidebar:
   * **Gemini API Key**: Obtain from [Google AI Studio](https://aistudio.google.com/).
   * **SerpAPI API Key**: Obtain from [SerpAPI](https://serpapi.com/) (Google Flights & Hotels wrapper).
   * **SendGrid API Key**: Obtain from [SendGrid](https://sendgrid.com/) (for email automation).

4. Enter your travel query in the textbox (e.g., *"I want to travel to Dehradun from Delhi for 7 days starting tomorrow. Find me flights and 4-star hotels"*), click **Get Travel Information**, and let Yatra Sathi compile your plan!

---

## 🔒 Security & Best Practices
Your API keys are stored temporarily in your local session and environment while the app is active. They are **never** committed to the repository. 

* The project includes a `.gitignore` file that automatically excludes your private environment configs (`.env`) and virtual environments (`.venv`).
* A template configuration file [`.env.example`](.env.example) is provided as a reference.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
