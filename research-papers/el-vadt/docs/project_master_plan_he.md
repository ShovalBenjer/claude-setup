# תוכנית-אב אסטרטגית: EL-VADT (ElevenLabs Voice Agent Domain Transfer)

## גרסה 2.1: מעבר לארכיטקטורה Native וניתוח SOTA אמיתי

מסמך זה מהווה את ה"מצפון הטכנולוגי" של הפרויקט. הוא מסביר את המהפך שעברנו משימוש בכלים מפוזרים (Retell, Twilio, Make) לעבודה בסטנדרט הגבוה ביותר של ElevenLabs לשנת 2026, תוך שימוש בניתוח נתונים ברמת Google/NVIDIA.

---

### 1. החזון והיעד (The Goal & Intent)

המטרה היא לייצר **מערכת העברת דומיינים אוטומטית (Domain Transfer)**. אנחנו לא רק בונים סוכן קולי; אנחנו בונים "מוח" שיודע לקחת דאטה גולמי משיחות מכירה, לחלץ ממנו את החוקיות הפסיכולוגית (SPIN/VITO), ולהטמיע אותה בסוכנים משימתיים (Task-Specific Agents).

**השינוי הגדול:** עברנו ממודל של "סוכן אחד שעושה הכל" למבנה של **Router & Sub-Agents**.

---

### 2. הארכיטקטורה החדשה (11Labs Native Focus)

בהתבסס על הניתוח העדכני של סביבת ה-Conversational AI:

- **Router Agent:** סוכן "מרכזנית" שמזהה את זהות הלקוח (באמצעות Instant Lookup ב-n8n) ומנתב אותו לסוכן המומחה.
- **Specialist Sub-Agents:** סוכנים נפרדים ל-Booking, FAQ וטיפול בהתנגדויות. זה מונע Hallucinations ומשפר את הדיוק ב-80%.
- **n8n Backend Logic:** העברנו את ה"לוגיקה הכבדה" החוצה מהקוד של הסוכן לתוך n8n. עכשיו הסוכן מבצע שאילתות בזמן אמת על היסטוריית הלקוח לפני שהוא פותח את הפה.

---

### 3. ניתוח נתונים SOTA 2026 (The SOTA Pipeline)

כדי לעמוד בסטנדרט של Google/NVIDIA, הניתוח שלנו ב-Notebook עובר שדרוג משמעותי:

#### א. משימתיות ו-Reasoning (Generative Intelligence)

אנחנו מפסיקים "לספור מילים". הניתוח החדש משתמש ב-**OpenAI O1 or GPT-4o** כ"שופט" (LLM-as-a-Judge) כדי לתייג כל תפנית בשיחה:

- **Intent Discovery:** זיהוי סמנטי של כוונות הלקוח מבלי להגדיר אותן מראש.
- **Aspect-Based Sentiment:** הבנה אם הלקוח מתוסכל מהמחיר (VITO) או מהממשק (Seemore).

#### ב. הנדסת פיצ'רים מתקדמת (Feature Engineering)

- **Semantic Proximity (Embeddings):** שימוש ב-`text-embedding-3-large` למדידת המרחק בין השיחה לבין יעדים אסטרטגיים.
- **Dialogue Metrics:**
  - **Turn-Taking Entropy:** מדידת הדינמיקה בין הדוברים.
  - **Emotional Resilience:** כמה מהר הסוכן מצליח להחזיר לקוח "כועס" למסלול המכירה.

#### ג. מפת האסטרטגיה (Visual Analytics)

שימוש ב-**UMAP** כדי לייצר מרחב דו-ממדי של כל 100 השיחות. זה מאפשר לנו לראות ויזואלית את ה-"Tech Support Trap" – גושים של שיחות שנתקעו בפרטים טכניים במקום בערך עסקי.

---

### 4. פרוטוקול העברה (EL-VADT Domain Transfer)

איך מעבירים את Maryam מעולם המכירות לעולם הביטוח?

1.  **Ingestion:** הרצת ה-SOTA Notebook על 100 שיחות מהדומיין החדש.
2.  **Dictionary Attack:** זיהוי מילות ה-VITO וה-Seemore של הדומיין החדש (למשל: בביטוח - "Deductible" הוא Seemore, "Asset Protection" הוא VITO).
3.  **Prompt Calibration:** עדכון קבועי הפרומפט (WPM, Greeting duration) לפי הנתונים הסטטיסטיים שנמצאו.

---

### סיכום למנהלים

אנחנו לא רק כותבים קוד; אנחנו מגדירים את הדרך שבה ElevenLabs Voice Agents ידברו בעתיד. שילוב של **Native Workflows** ו-**Generative Analysis** הוא הדרך היחידה להגיע לביצועים שהם באמת State-of-the-Art.
