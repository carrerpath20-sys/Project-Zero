## 🧭 **Project-Zero: সম্পূর্ণ ইউজার গাইড**  
*(Zero Recon Framework v2.0 — Level 5)* (private property , not allowed for public use for some vulnerabilities)

---

### 📌 **১. পরিচিতি (এটা কী?)**
**Project-Zero** (অভ্যন্তরীণ নাম: `Zero Recon Framework`) হলো একটি **এআই-চালিত, মডুলার রিকনেসান্স অটোমেশন টুল**, যা বিশেষভাবে **বাগ বাউন্টি হান্টার**, **রেড-টিমার**, এবং **পেন্টেস্টারদের** জন্য ডিজাইন করা। এটি **ARTEMIS-স্টাইল মাল্টি-এজেন্ট আর্কিটেকচার** অনুসরণ করে, কিন্তু Windows-এ নেটিভভাবে চলে এবং **WAF/ফায়ারওয়াল বাইপাস**-এর জন্য অ্যাডভান্সড OPSEC ফিচার রাখে।

---

### 🚀 **২. কেন ব্যবহার করবেন?**
| সুবিধা | বিবরণ |
|---|---|
| **🤖 এআই-চালিত অর্কেস্ট্রেশন** | কাজের জটিলতা বুঝে Cerebras / OpenRouter দিয়ে স্বয়ংক্রিয়ভাবে মডেল সিলেক্ট করে। |
| **🛡️ স্টেলথ ও ওপসেক** | র্যান্ডম ইউজার-এজেন্ট, ডিলে, প্রক্সি রোটেটর — WAF ডিটেক্ট করে না। |
| **🧠 ১৫টি অ্যাডভান্সড রিকন ফেজ** | সাবডোমেইন, ASN, GitHub, ক্লাউড, JS হিডেন এন্ডপয়েন্ট, টেকওভার, CORS, ডিফারেন্সিয়াল স্ক্যান — সব এক ফ্রেমওয়ার্কে। |
| **🩹 সেলফ-হিলিং** | কোনো ফেজ ব্যর্থ হলে AI নিজেই কোড/স্ট্র্যাটেজি রি-রাইট করে। |
| **🔁 অটো-আপডেট** | GitHub রিপো থেকে নতুন ভার্সন নিজে থেকেই টেনে আনে। |
| **💻 Windows-নেটিভ** | WSL বা ভার্চুয়াল মেশিন ছাড়াই CMD থেকে সরাসরি চলে। |
| **📊 লাইভ ড্যাশবোর্ড** | Flask + SocketIO-ভিত্তিক রিয়েল-টাইম মনিটরিং (ব্রাউজারে)। |

---

### 📦 **৩. ফিচারসমূহ (সংক্ষেপে)**
- **১৫টি রিকন ফেজ** (CT লগ, TLS ফিঙ্গারপ্রিন্ট, ASN, GitHub Dork, Wayback + JS AST, Cloud Bucket, DNS Permutation, MassDNS, OSINT Graph, Takeover + CORS + Port Scan, Attack Surface, Report, Infrastructure Inference, Supply Chain Metadata, Continuous Diff)
- **ইভো-ডেল্টা কোর** (DNA, MCTS, Symbolic, Debate, Mutator, Reflector, Profiler)
- **হাইব্রিড AI রাউটার** (Cerebras Primary + OpenRouter Fallback + Key Rotation)
- **অটো-ইনস্টলার** (`massdns`, `subfinder` — winget/choco/scoop/GitHub)
- **ড্যাশবোর্ড** (লাইভ লগ, স্ট্যাটস, ইভো মেটাডাটা)

---

### 🛠️ **৪. ইনস্টলেশন গাইড**

#### **পূর্বশর্ত (Prerequisites)**
- **Python 3.8 বা তার বেশি** ([python.org](https://python.org) থেকে ডাউনলোড করুন, ইনস্টলের সময় "Add Python to PATH" টিক দিতে ভুলবেন না)
- **Git** (ঐচ্ছিক, কিন্তু রেকমেন্ডেড)

#### **ধাপ ১: রিপো ক্লোন করা**
```cmd
git clone https://github.com/carrerpath20-sys/Project-Zero.git
cd Project-Zero
```

#### **ধাপ ২: ডিপেন্ডেন্সি ইনস্টল (অটোমেটিক)**
আপনি **একটি কমান্ডেই** সব Python লাইব্রেরি এবং এক্সটার্নাল টুলস (`massdns`, `subfinder`) ইনস্টল করতে পারেন:

```cmd
python main.py example.com --auto-install
```
👉 এটি প্রথমে `requirements.txt` থেকে সব প্যাকেজ ইনস্টল করবে, তারপর `massdns` ও `subfinder` খুঁজবে, না থাকলে `winget`/`choco`/`scoop` বা GitHub থেকে ডাউনলোড করবে।

**অথবা, শুধু ইনস্টলেশন (স্ক্যান ছাড়া):**
```cmd
python -m pip install -r requirements.txt
python -c "from tools.installer import ensure_tool; ensure_tool('massdns', auto_install=True); ensure_tool('subfinder', auto_install=True)"
```

#### **ধাপ ৩: API Keys সেটআপ**
`.env.example.txt` ফাইলটি কপি করে `.env` নাম দিন এবং আপনার API Keys বসান:
```env
OPENROUTER_API_KEY="sk-or-v1-xxxxx"
CEREBRAS_API_KEY="csk-xxxxx"
GITHUB_TOKEN=""
```
> **দ্রষ্টব্য:** `config.yaml`-এ ইতিমধ্যেই ডিফল্ট কী বসানো আছে, তবে `.env` ব্যবহার করলে বেশি নিরাপদ।

#### **ধাপ ৪: টেস্ট রান**
```cmd
python main.py example.com --phases 1,2,3 --verbose
```

---

### ⚙️ **৫. ব্যবহারের পদ্ধতি (বিভিন্ন মোড)**

#### **ক. বেসিক স্ক্যান (সব ফেজ)**
```cmd
python main.py target.com
```

#### **খ. গড-মোড (MCTS + Symbolic + Mutator + Reflector)**
```cmd
python main.py target.com --god-mode
```
👉 এটি AI-কে ৩টি পাথ চিন্তা করে বেস্টটি সিলেক্ট করতে বলে এবং কাস্টম রুলস জেনারেট করে।

#### **গ. অ্যাগ্রেসিভ ডিবেট (Attacker vs Defender)**
```cmd
python main.py target.com --god-mode --aggressive-debate
```
👉 WAF বাইপাস ভেরিফিকেশন — API খরচ ২-৩ কল বাড়ে, কিন্তু ডিটেকশন রেট ৯৮% হয়।

#### **ঘ. ড্যাশবোর্ড চালু করা**
```cmd
python main.py target.com --dashboard
```
👉 ব্রাউজারে `http://localhost:5000` ওপেন করলে লাইভ মনিটরিং দেখতে পাবেন।

#### **ঙ. শুধু নির্দিষ্ট ফেজ চালানো**
```cmd
python main.py target.com --phases 1,2,3,4
```

#### **চ. অটো-রেজিউম (ক্র্যাশের পর আবার শুরু)**
```cmd
python main.py target.com --resume <session_id>
```
👉 `session_id` পাবেন `state/session.json`-এ।

#### **ছ. ভার্বোস লগ (ডিবাগিং)**
```cmd
python main.py target.com --verbose
```
@@@ প্রফেশনাল কম্বো: python main.py target.com --phases 1,2,4,8,10,12 --verbose
---

### 📋 **৬. কমান্ড-লাইন আর্গুমেন্টের তালিকা**

| আর্গুমেন্ট | শর্ট | কাজ |
|---|---|---|
| `target` | (required) | টার্গেট ডোমেইন (যেমন: `example.com`) |
| `--config` | `-c` | কনফিগ ফাইলের পাথ (ডিফল্ট: `config.yaml`) |
| `--verbose` | `-v` | ডিটেইলড লগ দেখায় |
| `--auto-install` | `-a` | মিসিং ডিপেন্ডেন্সি ও টুলস অটো-ইনস্টল করে |
| `--resume` | `-r` | আগের সেশন থেকে শুরু করে |
| `--phases` | `-p` | কমা দিয়ে ফেজ নম্বর (যেমন: `1,2,5`) |
| `--output` | `-o` | আউটপুট ডিরেক্টরি (ডিফল্ট: `outputs`) |
| `--all` | - | সব ১৫টি ফেজ চালায় |
| **Level 5 এক্সক্লুসিভ** | | |
| `--god-mode` | - | MCTS, Symbolic, Mutator, Reflector সক্রিয় করে |
| `--aggressive-debate` | - | Adversarial Debate চালু করে (API কল বাড়ে) |
| `--dashboard` | - | ড্যাশবোর্ড সার্ভার চালু করে (`http://localhost:5000`) |

---

### 📊 **৭. আউটপুট ও রিপোর্ট**
স্ক্যান শেষ হলে `outputs/` ফোল্ডারে নিচের ফাইলগুলো তৈরি হবে:

| ফাইল/ফোল্ডার | পাথ | বিবরণ |
|---|---|---|
| **লগ ফাইল** | `outputs/logs/zero_recon_*.log` | পুরো স্ক্যানের বিস্তারিত লগ |
| **JSON রিপোর্ট** | `outputs/reports/report_*.json` | সব ডাটা মেশিন-রিডেবল JSON ফরম্যাটে |
| **HTML রিপোর্ট** | `outputs/reports/report_*.html` | ব্রাউজারে খোলার ড্যাশবোর্ড |
| **Markdown রিপোর্ট** | `outputs/reports/report_*.md` | মার্কডাউন ফরম্যাট |
| **ফেজ ডাটা** | `outputs/phase_data/phase_*.json` | প্রতিটি ফেজের কাঁচা ডাটা |

---

### ❓ **৮. ট্রাবলশুটিং (সাধারণ সমস্যা ও সমাধান)**

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `'python' is not recognized` | Python PATH-এ নেই | Python রি-ইনস্টল করুন, "Add to PATH" টিক দিন |
| `ModuleNotFoundError: No module named 'yaml'` | `pyyaml` ইনস্টল নেই | `pip install -r requirements.txt` রান করুন |
| `Cerebras API error 401` | API Key ভুল | `config.yaml` বা `.env`-এ কী চেক করুন |
| `MassDNS not found` | MassDNS ইনস্টল নেই | ফ্রেমওয়ার্ক Python ফ্যালব্যাক ব্যবহার করবে (ধীর) |
| স্ক্যান ধীরে চলছে | `max_threads: 1` | `config.yaml`-এ `max_threads: 10` করুন (নেটওয়ার্ক স্পিড অনুযায়ী) |
| `PermissionError` on Windows | Antivirus/Firewall ব্লক করছে | ফোল্ডারটি এক্সেপশন লিস্টে যোগ করুন অথবা অ্যাডমিন মোডে রান করুন |
| ড্যাশবোর্ড চালু হচ্ছে না | Flask ইনস্টল নেই | `pip install flask flask-socketio eventlet` দিন |

---

### ⚠️ **৯. লাইসেন্স ও দায়িত্ব**
- **লাইসেন্স:** Apache 2.0
- **দায়িত্ব:** এই টুল শুধুমাত্র **অনুমোদিত টার্গেটে** (যেমন: নিজের সার্ভার, বাগ বাউন্টি প্রোগ্রাম) ব্যবহারের জন্য। অননুমোদিত স্ক্যানিং অবৈধ। ব্যবহারকারী নিজেই দায়ী।

---

### 🔗 **১০. সহায়ক লিংক**
- **GitHub রিপো:** https://github.com/carrerpath20-sys/Project-Zero
- **API প্রোভাইডার:** [Cerebras](https://cerebras.ai), [OpenRouter](https://openrouter.ai)
- **রিপোর্ট ইস্যু:** GitHub Issues সেকশনে খুলুন।
