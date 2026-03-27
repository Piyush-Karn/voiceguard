# utils/chatbot.py

import chromadb
import requests
import os
import logging
import time
import json
from typing import Dict, List, Optional
from datetime import datetime

# --- Local Imports ---
from utils.database import get_chat_history, save_chat_message, clear_user_history as db_clear_history

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WomenSafetyChatbot:
    """Women Safety Legal Chatbot using direct REST API (no extra libraries)."""

    def __init__(self, api_key: str, chroma_path: str = "./chroma_db"):
        """
        Initialize the chatbot with settings.
        """
        try:
            self.api_key = api_key
            self.chroma_path = chroma_path
            
            # Use gemini-2.5-flash as the default
            self.model_name = os.getenv("MODEL_ID", "gemini-2.5-flash")
            
            # Initialize ChromaDB for RAG
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.chroma_client.get_collection("women_safety_laws")

            # 🌟 COMPREHENSIVE KEYWORD LIST
            self.safety_keywords = set([
                # --- English: Legal & Official ---
                "law", "legal", "police", "attack", "fir", "complaint", "court", "judge", "magistrate",
                "lawyer", "advocate", "rights", "ipc", "crpc", "section", "act", "warrant",
                "bail", "arrest", "custody", "divorce", "alimony", "maintenance", "dowry",
                "protection", "order", "dir", "shelter", "ngo", "commission", "ncw",
                
                # --- English: Abuse & Violence ---
                "abuse", "violence", "domestic", "hit", "beat", "slap", "kick", "punch",
                "push", "shove", "choke", "strangle", "burn", "acid", "weapon", "knife",
                "injury", "blood", "bruise", "hurt", "pain", "kill", "murder", "death",
                "torture", "cruelty", "harass", "harassment", "threat", "threatening",
                
                # --- English: Sexual & Cyber ---
                "rape", "assault", "molest", "molestation", "touch", "grope", "force",
                "sexual", "stalk", "stalking", "follow", "watch", "cyber", "online",
                "photo", "video", "leak", "blackmail", "nude", "porn", "sextortion",
                "trafficking", "bulling", "troll",
                
                # --- Hindi/Hinglish: Physical/Action ---
                "maar", "maarta", "peet", "pitai", "thappad", "danda", "laat", "ghusa",
                "chot", "khoon", "jalaya", "jala", "acid", "chaaku", "jaan", "marunga",
                "dabao", "zabardasti", "pakda", "khencha", "dhakka",
                
                # --- Hindi/Hinglish: Legal/Official ---
                "thana", "police", "daroga", "inspector", "report", "shikayat", "case",
                "kachehri", "kachahri", "adalat", "kanoon", "vakeel", "vakil", "insaaf",
                "nyay", "jail", "qaidi", "zamanat", "kagaz", "dahej",
                
                # --- Hindi/Hinglish: Abuse/Harassment ---
                "gali", "gaali", "galoch", "badtameezi", "pareshan", "tana", "taana",
                "dhamki", "dara", "dar", "khauf", "bhay", "sharam", "izzat",
                "chhed", "chhedkhani", "ashleel", "ganda", "message", "call",
                "balatkar", "rapist", "jism", "jismani", "atyaachaar", "atyachar",
                
                # --- Relationship Context ---
                "husband", "pati", "wife", "patni", "in-laws", "sasural", "saas", "sasur",
                "devar", "nanad", "family", "gharwale", "boyfriend", "lover", "partner",
                "live-in", "ex", "breakup", "marriage", "shaadi", "relationship",

                # --- 🌟 Proper Hindi (Devanagari) Keywords 🌟 ---
                "मारपीट", "हिंसा", "दहेज", "प्रताड़ना", "गाली", "धमकी", "बलात्कार", "रेप",
                "छेड़छाड़", "तेजाब", "हमला", "चोट", "हत्या", "खून", "जबरदस्ती", "शारीरिक",
                "मानसिक", "यौन", "शोषण", "तलाक", "गुस्सा", "डर", "पीछा", "परेशान",
                "गला घोंटना", "जलाना", "पीटना", "नोचना", "धक्का", "जख्म", "वार", "अभद्र",
                "अश्लील", "ब्लैकमेल", "तस्करी", "बंधक", "किडनैप", "अपहरण", "पुलिस", "थाना",
                "कोर्ट", "कचहरी", "वकील", "जज", "कानून", "अधिकार", "शिकायत", "एफआईआर",
                "रिपोर्ट", "गिरफ्तार", "जमानत", "सजा", "इंसाफ", "न्याय", "केस", "महिला आयोग",
                "धारा", "अधिनियम", "हक", "बयान", "जांच", "गवाह", "सबूत", "हिरासत", "वारंट",
                "भरण-पोषण", "गुजारा भत्ता", "संरक्षण", "आश्रय", "मदद", "सहायता", "मुकदमा",
                "तारीख", "फैसला", "पति", "पत्नी", "ससुराल", "सास", "ससुर", "दहेज़", "शादी",
                "विवाह", "रिश्ता", "तलाक", "अकेली", "बेटी", "बहन", "जेठ", "देवर", "ननद",
                "मायके", "दूसरी औरत", "चक्कर", "शक", "नशा", "शराब", "जबरन", "बाल विवाह",
                "गर्भवती", "सौतन", "बचाओ", "आत्महत्या", "मरना", "फंसी", "मजबूर", "रो रही",
                "घबराहट"
            ])

            logger.info(f"✅ Chatbot initialized with {self.model_name} via Direct REST API.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize chatbot: {str(e)}")

    def search_laws(self, query: str, n_results: int = 3) -> List[str]:
        """Search ChromaDB for relevant law sections."""
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            documents = results.get('documents', [[]])[0]
            return documents if documents else ["No specific legal context found."]
        except Exception as e:
            logger.error(f"❌ Error searching laws: {str(e)}")
            return ["Unable to retrieve legal context."]

    def build_system_prompt(self) -> str:
        """Build the system prompt for the LLM."""
        return """You are Asha, a women's safety assistant for India. Your specialty is women's safety, rights, and Indian law.
        
        LANGUAGE: Always respond in the SAME language as the user (English/Hindi/Hinglish/Regional).
        
        RESPONSE STYLE:
        1. LEGAL & DETAILED: Use if the user asks about laws, IPC sections, or rights. Be formal and mention specific laws (IPC/CrPC/DV Act).
        2. EMPATHETIC: If the user mentions abuse or fear, be supportive first, then provide steps.
        3. EMERGENCY: ALWAYS tell them to call 112 or 181 if they are in immediate danger.
        
        You have RAG access to legal context. Use it accurately.
        """

    def _should_skip_db_search(self, message: str) -> bool:
        """Heuristic to skip DB search for non-legal/non-safety queries."""
        message_lower = message.lower()
        words = message_lower.split()
        if len(words) < 2 and message_lower not in self.safety_keywords:
            return True
        if message_lower.startswith(('what', 'how', 'why', 'who', 'when', 'where', 'can i', 'is it', 'kya', 'kaise', 'kyun')):
            return False
        for word in words:
            for keyword in self.safety_keywords:
                if keyword in word: return False
        return True

    def call_gemini_rest(self, message: str, history: List[Dict]) -> str:
        """Call Gemini API via direct REST request."""
        url = f'https://generativelanguage.googleapis.com/v1/models/{self.model_name}:generateContent?key={self.api_key}'
        
        headers = {'Content-Type': 'application/json'}
        
        # Construct the content list
        contents = []
        
        # Add a combined system prompt + first message if no history
        # Or prepend system prompt to the current message if history exists
        system_instruction = self.build_system_prompt()
        
        # Gemini v1 API for generateContent doesn't have a separate 'system' role in the contents list easily like OpenAI.
        # It's better to prepand it to the first user message or use the system_instruction parameter (but that's in a different field).
        # We'll use the user's approach of putting it in the text.
        
        # Add history
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": h["content"]}]
            })
            
        # Add current message with system context if it's the first message
        if not contents:
            full_context_message = f"{system_instruction}\n\nUSER: {message}"
        else:
            full_context_message = message
            
        contents.append({
            "role": "user",
            "parts": [{"text": full_context_message}]
        })

        data = {"contents": contents}

        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'candidates' in res_json and len(res_json['candidates']) > 0:
                    text = res_json['candidates'][0]['content']['parts'][0]['text']
                    return text
                return "I'm having trouble thinking of a response right now. Please try again."
            else:
                logger.error(f"❌ REST API Error: {response.status_code} - {response.text}")
                return f"An AI error occurred (Status {response.status_code})."
                
        except Exception as e:
            logger.error(f"❌ Exception in call_gemini_rest: {e}")
            return "An AI error occurred. For emergencies, please call 112 directly."

    def chat(self, user_id: str, message: str, language: str = "english") -> Dict:
        """Main chat function with REST API and RAG."""
        start_time = time.time()
        try:
            # 1. RAG Search
            context = ""
            if not self._should_skip_db_search(message):
                legal_docs = self.search_laws(message)
                context = "\n\n".join(legal_docs)

            # 2. Get History
            history = get_chat_history(user_id)
            
            # 3. Final Prompt
            full_prompt = message
            if context:
                full_prompt = f"LEGAL CONTEXT:\n{context}\n\nUSER QUESTION: {message}"

            # 4. Generate
            response_text = self.call_gemini_rest(full_prompt, history)

            # 5. Save & Return
            save_chat_message(user_id, "user", message)
            save_chat_message(user_id, "assistant", response_text)

            return {
                "success": True,
                "response": response_text,
                "timestamp": datetime.now().isoformat(),
                "processing_time": round(time.time() - start_time, 2)
            }

        except Exception as e:
            logger.error(f"❌ Chatbot error: {e}")
            return {"error": str(e), "success": False}

    def clear_user_history(self, user_id: str):
        """Clear conversation history for a user from the database."""
        logger.info(f"Attempting to clear history for user {user_id}...")
        db_clear_history(user_id)

    def get_stats(self) -> Dict:
        return {
            "active_users": "Stored in MongoDB",
            "model": self.model_name,
            "chroma_path": self.chroma_path,
            "engine": "Direct Google REST API"
        }