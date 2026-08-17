# The Robot Helpdesk — Explained Like You're 12

## What are we building?

Imagine a big company that makes hospital machines — MRI scanners, X-ray machines, patient monitors. Hundreds of hospitals buy these machines, and they have questions all day long:

- "Where is my order? It was supposed to arrive Tuesday."
- "My scanner is broken, I need a technician."
- "Is my warranty still valid?"
- "What warranty comes with new equipment?"
- "Can you send me the FDA certificate?"

Normally a human support team answers all of this. That's slow and expensive. So we built a **robot helper you chat with** (like texting a friend) that answers these questions instantly, 24/7. It's called a **chatbot**.

## The big idea: the robot has two different brains

Here's the clever part. Questions come in two flavors, so our robot uses **two different tools** depending on the question.

**Brain 1 — the Filing Cabinet (the "SQL" part).**
Some answers live in a giant organized table, like a spreadsheet: your order number, delivery date, warranty end-date, invoice amount. These are *facts about you* stored in neat rows. The robot looks up your row. Computers use a language called **SQL** to ask tables questions. Think of it as a super-organized filing cabinet.

**Brain 2 — the Library (the "RAG" part).**
Other answers live in documents — user manuals, warranty policies, how-to guides, certificates. These aren't neat rows; they're pages of writing. So the robot acts like a smart librarian: it reads your question, runs to the right shelf, pulls out the matching paragraph, and reads it back in plain words. This trick is called **RAG** — *Retrieval-Augmented Generation*. Fancy name, simple idea: **look it up first, then answer** (never guess).

## The assembly line (this is the "n8n" part)

The whole robot is built as an **assembly line** using a tool called **n8n**. Picture a conveyor belt with stations. Your question is a box that rides the belt, and each station does one job before passing it along:

1. **The mail slot (Webhook).** Your chat message drops in here and gets on the belt.

2. **The door guard (Auth).** Before sharing anything private, this station checks who you are — your email + a client ID — like showing a library card. If the card doesn't match, the box is sent to the "Sorry, can't verify you" chute and never reaches your data. This protects patients' and hospitals' information.

3. **The sorting hat (Classify Intent).** It reads your message and figures out *what kind* of question it is — an "order status" question, a "warranty" question, a "how-to" question, and so on. There are 9 kinds it knows.

4. **The traffic cop (Route).** Now it decides which brain to use. And it's clever about it:
   - "Where is **my** order?" or "Is **my** warranty active?" → *facts about you* → go to the **filing cabinet** (SQL).
   - "**What** warranty comes with new equipment?" or "How do I book maintenance?" → *general policy / how-to* → go to the **library** (RAG).

   Notice the trick: the same topic (warranty) can go to *either* brain depending on whether you're asking about **your** stuff or about the **rules**.

5. **The safety net (try the cabinet, then the library).** If the robot checks the filing cabinet and finds nothing about you, it doesn't just give up — it *then* asks the librarian before answering. This is called a **cascade**: try the exact facts first, fall back to the documents, and only then say "I don't know."

6. **The honest answer.** If neither brain can help, the robot says *"I don't know the answer to that."* A good helper never bluffs.

7. **The diary (Audit Log).** Every chat is quietly written down — who asked, when, what kind of question, which brain answered. You can even open a web page (`/history`) and see the whole diary, like a logbook.

## Why it's fast (under 2 seconds)

Thinking with the big AI is powerful but a little slow — like asking a professor a question. So for the easy, common questions (your orders, your warranty, your invoices), the robot skips the professor and just reads a fixed page in the filing cabinet. That's **instant** (a fraction of a second). It only wakes up the big AI for the harder library questions that need real writing. Result: most answers come back faster than you can blink.

## The alarm (the Error Handler)

Machines break sometimes. So there's a second little assembly line that does nothing… until the main robot trips and falls. The moment something goes wrong, this **alarm** wakes up, writes down exactly what broke (and where), and can even email the grown-ups so they fix it fast.

## The safety rules (super important in healthcare)

- The robot can **only look up YOUR data**, never another hospital's. Every filing-cabinet lookup is locked to your client ID.
- The robot can **only read** the tables, never change or delete them.
- Every chat is written in the diary so the company can check that everything stayed safe. This is the "HIPAA-like" rule mentioned in the project.
- The robot even **cleans up messy questions** before using them, so a stray typo or extra symbol can't confuse the filing cabinet.

## The pieces we actually built (the parts list)

| Piece | What it is | Kid version |
|---|---|---|
| Chat message in | A web page / API you type into | The talking window |
| Auth | Email + client ID check | The door guard |
| Classify Intent | AI that labels the question | The sorting hat |
| Route | Chooses SQL or RAG | The traffic cop |
| SQL engine | Reads the database safely & fast | The filing cabinet |
| RAG engine | Searches the documents | The librarian |
| Cascade | SQL first, then RAG, then "I don't know" | The safety net |
| Database | Tables of orders/warranty/etc. | The cabinet's drawers |
| Documents | Manuals, policies, certificates | The library shelves |
| Audit log + /history | Records every chat | The diary you can read |
| Error handler | Runs only when things break | The alarm |
| n8n | Connects all the stations | The conveyor belt |

## What "done" looks like

You send a message. The door guard checks your card. The sorting hat labels your question. The traffic cop sends it to the filing cabinet or the library (and tries the other one if the first comes up empty). You get a clear answer in about a second — or an honest "I don't know." And everything you did lands in the diary. If the robot ever trips, an alarm goes off. That's the whole project. 🎉

*(The grown-up technical version of all this is in `ARCHITECTURE.md` and `README.md`.)*
