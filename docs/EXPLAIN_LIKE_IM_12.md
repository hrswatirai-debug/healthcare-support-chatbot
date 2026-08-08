# The Robot Helpdesk — Explained Like You're 12

## What are we building?

Imagine a big company that makes hospital machines — MRI scanners, X-ray machines, patient monitors. Hundreds of hospitals buy these machines. And hospitals have questions all day long:

- "Where is my order? It was supposed to arrive Tuesday."
- "My scanner is broken, I need a technician."
- "Is my warranty still valid?"
- "Can you send me the FDA safety certificate?"

Normally a human support team answers all of this. That's slow and expensive. So we're building a **robot helper you chat with** (like texting a friend) that answers these questions instantly, 24/7. It's called a **chatbot**.

## The big idea: the robot has two different brains

Here's the clever part. Questions come in two flavors, so our robot uses **two different tools** depending on the question.

**Brain 1 — the Filing Cabinet (this is the "SQL" part).**
Some answers live in a giant organized table, like a spreadsheet. Your order number, your delivery date, your warranty end-date, your invoice amount — these are *facts about you* stored in rows and columns. To get them, the robot looks up your row in the table. Computers use a language called **SQL** to ask tables questions ("find order #4402 and tell me its status"). Think of it as a super-organized filing cabinet.

**Brain 2 — the Library (this is the "RAG" part).**
Other answers live in documents — user manuals, safety policies, how-to guides. These aren't neat rows; they're pages of writing. So the robot acts like a smart librarian: it reads the question, runs to the right shelf, pulls out the paragraph that matches, and reads it back to you in plain words. This trick is called **RAG** — *Retrieval-Augmented Generation*. Fancy name, simple idea: **look it up first, then answer** (instead of guessing).

## Why two brains? Why not one?

Because guessing is dangerous, especially in healthcare. If you ask an AI "what's my warranty date?" and it just *makes up* an answer, that's bad. So:

- Facts about **you** → look them up in the **table** (SQL). Always exact.
- **How-to / policy / manual** questions → look them up in the **documents** (RAG). Always based on a real page.
- If the robot **can't find** the answer anywhere → it honestly says *"I don't know the answer to that."* (A good helper never bluffs.)

## How a single question travels through the robot (the journey)

1. **The door (Login).** Before answering anything private, the robot checks who you are — your email + a client ID — like showing a library card. No card, no private data. This protects patients' and hospitals' information.

2. **The sorting hat (Intent detection).** You type "Where's my MRI order?" The robot figures out *what kind* of question this is — an "Order Status" question. This step is called **intent detection**. There are 9 kinds of questions it knows (orders, warranty, complaints, spare parts, certificates, etc.).

3. **The traffic cop (Routing).** Now the robot decides which brain to use. "Order status" = a fact about you = go to the **SQL filing cabinet**. "How do I clean the scanner?" = a how-to = go to the **RAG library**.

4. **The answer.** It fetches the real answer and writes it back to you in a friendly sentence — sometimes with a link to a manual PDF.

5. **The diary (Logging).** The robot quietly writes down "someone asked about orders at 3pm, we used the filing cabinet" — so the company can check later that everything worked and stayed safe. This is called an **audit log**.

## The safety rules (super important in healthcare)

- The robot can **only look up YOUR data**, never another hospital's. We force every table lookup to be locked to your client ID.
- The robot can **only read** the tables, never change or delete them.
- Every chat is logged so a grown-up (the company) can audit it — this is the "HIPAA-like" rule mentioned in the project.

## The pieces we're actually building (the parts list)

| Piece | What it is | Kid version |
|---|---|---|
| Chat screen | A web page you type into | The talking window |
| Login | Email + client ID check | The library card scanner |
| Intent classifier | AI that labels the question | The sorting hat |
| Router | Chooses SQL or RAG | The traffic cop |
| SQL engine | Reads the database safely | The filing cabinet |
| RAG engine | Searches the documents | The librarian |
| Database | Tables of orders/warranty/etc. | The filing cabinet's drawers |
| Documents | Manuals, policies, certificates | The library shelves |
| Logger | Records every chat | The diary |

## What "done" looks like

You open a web page, log in with an email + client ID, and chat. You ask about your order — it looks it up. You ask how to book maintenance — it reads the policy back to you. You ask something silly it doesn't know — it politely says it doesn't know. And everything you did is written in the diary. That's the whole project. 🎉

*(The grown-up technical version of all this is in `ARCHITECTURE.md` and `README.md`.)*
