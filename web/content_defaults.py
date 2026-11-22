"""Default storefront lists and policy pages (English + Bangla).

`manage.py sync_content` creates these rows only where none exist, so
anything edited in the admin is never overwritten. Page *text* defaults
come from the {% cms %} tags in the templates themselves.

Policy pages are starting drafts — check them (especially the return
window and privacy details) before the shop goes live.
"""

# group -> rows of (icon, value_en, value_bn, title_en, title_bn, text_en, text_bn)
ITEMS = {
    "home.hero_trust": [
        ("shield", "", "", "1-Year Warranty", "১ বছরের ওয়ারেন্টি", "", ""),
        ("truck", "", "", "Cash on Delivery", "ক্যাশ অন ডেলিভারি", "", ""),
        ("award", "", "", "FCC · CE · RoHS", "FCC · CE · RoHS", "", ""),
    ],
    "home.spotlight_points": [
        ("", "", "", "Motorized locking", "মোটরচালিত লকিং",
         "— quiet, smooth and tamper-resistant", "— নিঃশব্দ, মসৃণ ও সহজে ভাঙা যায় না"),
        ("", "", "", "Fits doors thicker than 3 mm", "৩ মিমি-এর বেশি পুরু দরজায় লাগে",
         "— cabinets, drawers, wardrobes, lockers", "— ক্যাবিনেট, ড্রয়ার, ওয়ারড্রোব, লকার"),
        ("", "", "", "Low power use", "কম বিদ্যুৎ খরচ",
         "with a low-battery reminder", "— সাথে লো-ব্যাটারি রিমাইন্ডার"),
        ("", "", "", "External USB emergency power", "বাইরের ইউএসবি ইমার্জেন্সি পাওয়ার",
         "if the battery ever runs flat", "— ব্যাটারি শেষ হয়ে গেলেও খোলা যায়"),
        ("", "", "", "Minimalist black ABS", "মিনিমালিস্ট কালো ABS",
         "body that suits any furniture", "বডি, যেকোনো আসবাবে মানানসই"),
    ],
    "home.applications": [
        ("archive", "", "", "Cabinets", "ক্যাবিনেট", "", ""),
        ("drawer", "", "", "Drawers", "ড্রয়ার", "", ""),
        ("home", "", "", "Wardrobes", "ওয়ারড্রোব", "", ""),
        ("grid", "", "", "Lockers", "লকার", "", ""),
        ("briefcase", "", "", "Offices", "অফিস", "", ""),
        ("bed", "", "", "Hotels", "হোটেল", "", ""),
        ("hospital", "", "", "Hospitals", "হাসপাতাল", "", ""),
        ("activity", "", "", "Gyms & spas", "জিম ও স্পা", "", ""),
    ],
    "home.steps": [
        ("", "", "", "Mount it", "লাগিয়ে নিন",
         "Fix the round keypad on the front and screw the lock body inside the door (3 mm+ thickness).",
         "গোল কিপ্যাডটি সামনে লাগান এবং লক বডিটি দরজার ভেতরে স্ক্রু দিয়ে আটকান (৩ মিমি+ পুরুত্ব)।"),
        ("", "", "", "Set your codes", "কোড সেট করুন",
         "Create a management code for the owner and a user code for daily access.",
         "মালিকের জন্য ম্যানেজমেন্ট কোড এবং প্রতিদিনের ব্যবহারের জন্য ইউজার কোড তৈরি করুন।"),
        ("", "", "", "Pick a mode", "মোড বেছে নিন",
         "Choose public mode for visitors or private mode for a fixed personal code.",
         "ভিজিটরদের জন্য পাবলিক মোড অথবা নির্দিষ্ট ব্যক্তিগত কোডের জন্য প্রাইভেট মোড বেছে নিন।"),
        ("", "", "", "Tap & open", "চাপুন আর খুলুন",
         "Enter the code and the motor unlocks. USB keys and USB power are your backup.",
         "কোড দিলেই মোটর লক খুলে দেয়। ইউএসবি চাবি ও ইউএসবি পাওয়ার আপনার ব্যাকআপ।"),
    ],
    "home.stats": [
        ("", "2", "২", "Password sets", "পাসওয়ার্ড সেট", "", ""),
        ("", "1 + 3", "১ + ৩", "USB keys (main + management)", "ইউএসবি চাবি (মেইন + ম্যানেজমেন্ট)", "", ""),
        ("", "Ø 50.5 mm", "Ø ৫০.৫ মিমি", "Compact keypad", "কমপ্যাক্ট কিপ্যাড", "", ""),
        ("", "1 Year", "১ বছর", "Warranty", "ওয়ারেন্টি", "", ""),
    ],
    "about.story_points": [
        ("check", "", "", "Genuine WaRa products only", "শুধুমাত্র আসল WaRa পণ্য", "", ""),
        ("check", "", "", "Honest pricing with cash on delivery", "ন্যায্য দাম, ক্যাশ অন ডেলিভারি সুবিধা", "", ""),
        ("check", "", "", "Real people on phone & WhatsApp", "ফোন ও হোয়াটসঅ্যাপে সত্যিকারের মানুষ", "", ""),
    ],
    "portfolio.stats": [
        ("", "Ø 50.5", "Ø ৫০.৫", "mm keypad diameter", "মিমি কিপ্যাডের ব্যাস", "", ""),
        ("", "60×86", "৬০×৮৬", "mm lock body (23.5 mm deep)", "মিমি লক বডি (২৩.৫ মিমি গভীর)", "", ""),
        ("", "3 mm+", "৩ মিমি+", "Suitable door thickness", "উপযুক্ত দরজার পুরুত্ব", "", ""),
        ("", "3", "৩", "Certifications: FCC, CE, RoHS", "সার্টিফিকেশন: FCC, CE, RoHS", "", ""),
    ],
    # The English title is what staff see in Messages, whatever the page language.
    "contact.subjects": [
        ("", "", "", "Product inquiry", "পণ্য সম্পর্কে জানতে", "", ""),
        ("", "", "", "Order status", "অর্ডারের অবস্থা", "", ""),
        ("", "", "", "Installation help", "লাগানোর সাহায্য", "", ""),
        ("", "", "", "Warranty & support", "ওয়ারেন্টি ও সাপোর্ট", "", ""),
        ("", "", "", "Bulk / corporate order", "পাইকারি / কর্পোরেট অর্ডার", "", ""),
    ],
    "cart.trust": [
        ("shield", "", "", "Genuine WaRa product", "আসল WaRa পণ্য", "", ""),
        ("cash", "", "", "Cash on delivery", "ক্যাশ অন ডেলিভারি", "", ""),
        ("truck", "", "", "Delivery all over BD", "সারা বাংলাদেশে ডেলিভারি", "", ""),
        ("award", "", "", "Official warranty", "অফিসিয়াল ওয়ারেন্টি", "", ""),
    ],
}


# slug -> page fields (English + Bangla). kind "faq" uses Q:/A: lines.
PAGES = [
    {
        "slug": "warranty-delivery",
        "kind": "text",
        "title_en": "Warranty & Delivery",
        "title_bn": "ওয়ারেন্টি ও ডেলিভারি",
        "intro_en": "How we deliver your order and what the warranty covers.",
        "intro_bn": "আমরা কীভাবে অর্ডার পৌঁছে দিই এবং ওয়ারেন্টিতে কী কী থাকে।",
        "body_en": """## Delivery
We deliver to all 64 districts of Bangladesh. Delivery charges and times are shown at checkout before you place the order.

- Inside Dhaka: usually 1–2 working days
- Outside Dhaka: usually 2–4 working days
- Our team calls you to confirm the order before it is shipped

## Payment
- Cash on delivery: pay the delivery person when the parcel arrives
- bKash or Nagad: send the amount shown at checkout and enter your transaction ID (TrxID); we confirm it by phone

## Warranty
WaRa products come with the warranty stated on the product page (1 year for the FT-SCL029) against manufacturing defects.

- Keep your order number — you need it for warranty support
- The warranty does not cover physical damage, water damage or wrong installation
- Contact us by phone or WhatsApp; we repair or replace a faulty product""",
        "body_bn": """## ডেলিভারি
আমরা বাংলাদেশের ৬৪ জেলায় ডেলিভারি দিই। অর্ডার করার আগেই চেকআউটে ডেলিভারি চার্জ ও সময় দেখানো হয়।

- ঢাকার ভেতরে: সাধারণত ১–২ কার্যদিবস
- ঢাকার বাইরে: সাধারণত ২–৪ কার্যদিবস
- পাঠানোর আগে আমাদের টিম ফোন করে অর্ডার নিশ্চিত করে

## পেমেন্ট
- ক্যাশ অন ডেলিভারি: পার্সেল হাতে পেয়ে ডেলিভারিম্যানকে টাকা দিন
- বিকাশ বা নগদ: চেকআউটে দেখানো টাকা পাঠিয়ে ট্রানজেকশন আইডি (TrxID) দিন; আমরা ফোনে নিশ্চিত করি

## ওয়ারেন্টি
WaRa পণ্যে পণ্যের পেজে উল্লেখিত ওয়ারেন্টি (FT-SCL029-এর জন্য ১ বছর) উৎপাদনজনিত ত্রুটির বিপরীতে প্রযোজ্য।

- অর্ডার নম্বরটি রেখে দিন — ওয়ারেন্টি সাপোর্টের জন্য এটি লাগবে
- শারীরিক ক্ষতি, পানিতে নষ্ট হওয়া বা ভুলভাবে লাগানো ওয়ারেন্টির আওতায় পড়ে না
- ফোন বা হোয়াটসঅ্যাপে যোগাযোগ করুন; ত্রুটিপূর্ণ পণ্য আমরা মেরামত বা বদলে দিই""",
        "order": 1,
    },
    {
        "slug": "return-refund-policy",
        "kind": "text",
        "title_en": "Return & Refund Policy",
        "title_bn": "রিটার্ন ও রিফান্ড নীতি",
        "intro_en": "What to do if something is wrong with your order.",
        "intro_bn": "অর্ডারে কোনো সমস্যা হলে কী করবেন।",
        "body_en": """## Check your parcel
Please check the product in front of the delivery person. If the box is damaged or the product is wrong, you can refuse the parcel.

## Returns
- Tell us within 3 days of delivery if the product is damaged, faulty or not what you ordered
- The product must be unused, with its box, accessories and USB keys
- Send a photo or video on WhatsApp so we can arrange the return quickly

## Refunds
- Cash on delivery orders: we replace the product or refund the amount you paid
- bKash / Nagad payments: refunds are sent back to the same number within 7 working days after we receive the returned product
- Delivery charges are refunded only when the mistake was ours""",
        "body_bn": """## পার্সেল যাচাই করুন
ডেলিভারিম্যানের সামনেই পণ্যটি দেখে নিন। বাক্স ক্ষতিগ্রস্ত হলে বা ভুল পণ্য এলে পার্সেল ফেরত দিতে পারেন।

## রিটার্ন
- পণ্য ক্ষতিগ্রস্ত, ত্রুটিপূর্ণ বা অর্ডারের সাথে না মিললে ডেলিভারির ৩ দিনের মধ্যে আমাদের জানান
- পণ্যটি অব্যবহৃত হতে হবে এবং বাক্স, আনুষঙ্গিক জিনিস ও ইউএসবি চাবি সহ থাকতে হবে
- দ্রুত রিটার্নের ব্যবস্থার জন্য হোয়াটসঅ্যাপে একটি ছবি বা ভিডিও পাঠান

## রিফান্ড
- ক্যাশ অন ডেলিভারি অর্ডার: আমরা পণ্য বদলে দিই অথবা পরিশোধিত টাকা ফেরত দিই
- বিকাশ / নগদ পেমেন্ট: ফেরত পণ্য পাওয়ার ৭ কার্যদিবসের মধ্যে একই নম্বরে টাকা ফেরত পাঠানো হয়
- ভুল আমাদের হলেই কেবল ডেলিভারি চার্জ ফেরত দেওয়া হয়""",
        "order": 2,
    },
    {
        "slug": "faq",
        "kind": "faq",
        "title_en": "Frequently Asked Questions",
        "title_bn": "সাধারণ প্রশ্ন ও উত্তর",
        "intro_en": "Quick answers about ordering, delivery, payment and the lock.",
        "intro_bn": "অর্ডার, ডেলিভারি, পেমেন্ট ও লক নিয়ে দ্রুত উত্তর।",
        "body_en": """Q: How do I place an order?
A: Add the product to your cart and check out, or call / WhatsApp us and we will take the order by phone.

Q: Why do I get an SMS code at checkout?
A: The code confirms your mobile number so the courier can reach you. You only need it once a day, and not at all when you are logged in.

Q: How long does delivery take?
A: Usually 1–2 working days inside Dhaka and 2–4 working days elsewhere in Bangladesh.

Q: Can I pay when the product arrives?
A: Yes. Cash on delivery is available all over Bangladesh. You can also pay in advance with bKash or Nagad.

Q: How do I track my order?
A: Use "Track your order" at the bottom of every page with your order number and mobile number, or log in to see all your orders.

Q: Do I need an electrician to install the lock?
A: No. There is no mains wiring — a drill and a screwdriver are enough, and we can guide you on WhatsApp.""",
        "body_bn": """Q: কীভাবে অর্ডার করব?
A: পণ্যটি কার্টে যোগ করে চেকআউট করুন, অথবা কল / হোয়াটসঅ্যাপ করুন — আমরা ফোনেই অর্ডার নিয়ে নেব।

Q: চেকআউটে এসএমএস কোড আসে কেন?
A: কোডটি আপনার মোবাইল নম্বর নিশ্চিত করে, যাতে কুরিয়ার আপনার সাথে যোগাযোগ করতে পারে। দিনে একবারই লাগে, আর লগইন থাকলে লাগেই না।

Q: ডেলিভারিতে কত দিন লাগে?
A: সাধারণত ঢাকার ভেতরে ১–২ কার্যদিবস এবং বাংলাদেশের অন্য জায়গায় ২–৪ কার্যদিবস।

Q: পণ্য হাতে পেয়ে কি টাকা দেওয়া যাবে?
A: হ্যাঁ। সারা বাংলাদেশে ক্যাশ অন ডেলিভারি আছে। চাইলে বিকাশ বা নগদে আগেও পেমেন্ট করতে পারেন।

Q: অর্ডার কীভাবে ট্র্যাক করব?
A: প্রতিটি পেজের নিচে "অর্ডার ট্র্যাক করুন"-এ অর্ডার নম্বর ও মোবাইল নম্বর দিন, অথবা লগইন করে সব অর্ডার দেখুন।

Q: লক লাগাতে কি ইলেকট্রিশিয়ান লাগবে?
A: না। কোনো বিদ্যুতের তার নেই — একটি ড্রিল আর স্ক্রুড্রাইভারই যথেষ্ট, আর হোয়াটসঅ্যাপে আমরা দেখিয়ে দিতে পারি।""",
        "order": 3,
    },
    {
        "slug": "privacy-policy",
        "kind": "text",
        "title_en": "Privacy Policy",
        "title_bn": "গোপনীয়তা নীতি",
        "intro_en": "What information we collect and how we use it.",
        "intro_bn": "আমরা কী তথ্য সংগ্রহ করি এবং কীভাবে ব্যবহার করি।",
        "body_en": """## What we collect
- Your name, mobile number, delivery address and (if you give it) email
- Your orders and messages you send us
- Basic technical data such as your browser and IP address, used to keep the site secure

## How we use it
- To deliver your order and contact you about it
- To send one-time SMS codes that verify your mobile number
- To answer your questions and provide warranty support

## Who we share it with
We share your name, phone number and address only with the courier that delivers your order and the SMS provider that sends your verification codes. We never sell your information.

## Your choices
You can update your name, email and addresses in My Account, or ask us to delete your account by calling or messaging us.""",
        "body_bn": """## আমরা কী সংগ্রহ করি
- আপনার নাম, মোবাইল নম্বর, ডেলিভারি ঠিকানা এবং (দিলে) ইমেইল
- আপনার অর্ডার ও আমাদের পাঠানো বার্তা
- সাইট নিরাপদ রাখতে ব্রাউজার ও আইপি ঠিকানার মতো সাধারণ কারিগরি তথ্য

## আমরা কীভাবে ব্যবহার করি
- আপনার অর্ডার পৌঁছে দিতে এবং সে বিষয়ে যোগাযোগ করতে
- মোবাইল নম্বর যাচাইয়ের জন্য এককালীন এসএমএস কোড পাঠাতে
- আপনার প্রশ্নের উত্তর ও ওয়ারেন্টি সাপোর্ট দিতে

## কার সাথে শেয়ার করি
আপনার নাম, ফোন নম্বর ও ঠিকানা শুধু অর্ডার পৌঁছে দেওয়া কুরিয়ার এবং যাচাই কোড পাঠানো এসএমএস প্রোভাইডারের সাথে শেয়ার করা হয়। আমরা কখনো আপনার তথ্য বিক্রি করি না।

## আপনার পছন্দ
মাই অ্যাকাউন্টে নাম, ইমেইল ও ঠিকানা বদলাতে পারেন, অথবা কল বা মেসেজ করে অ্যাকাউন্ট মুছে ফেলতে বলতে পারেন।""",
        "order": 4,
    },
    {
        "slug": "terms-and-conditions",
        "kind": "text",
        "title_en": "Terms & Conditions",
        "title_bn": "শর্তাবলি",
        "intro_en": "The rules for buying from WaRa BD.",
        "intro_bn": "WaRa BD থেকে কেনাকাটার নিয়মাবলি।",
        "body_en": """## Orders
An order is confirmed when our team calls you to confirm it. We may cancel an order if the product is out of stock, the address cannot be reached or the details look false.

## Prices
Prices are in Bangladeshi Taka (৳) and include VAT where applicable. The delivery charge is shown at checkout.

## Your account
You log in with your mobile number and a one-time SMS code. Keep your phone safe and never share the code with anyone — our staff will never ask for it.

## Warranty, returns and refunds
See our Warranty & Delivery and Return & Refund pages.

## Contact
For any question about these terms, call or WhatsApp us using the details at the bottom of the page.""",
        "body_bn": """## অর্ডার
আমাদের টিম ফোন করে নিশ্চিত করলে অর্ডার কনফার্ম হয়। পণ্য স্টকে না থাকলে, ঠিকানায় পৌঁছানো না গেলে বা তথ্য ভুল মনে হলে আমরা অর্ডার বাতিল করতে পারি।

## দাম
দাম বাংলাদেশি টাকায় (৳) এবং প্রযোজ্য ক্ষেত্রে ভ্যাটসহ। ডেলিভারি চার্জ চেকআউটে দেখানো হয়।

## আপনার অ্যাকাউন্ট
মোবাইল নম্বর ও এককালীন এসএমএস কোড দিয়ে লগইন করবেন। ফোন নিরাপদে রাখুন এবং কোড কাউকে দেবেন না — আমাদের কর্মীরা কখনো কোড চাইবে না।

## ওয়ারেন্টি, রিটার্ন ও রিফান্ড
আমাদের ওয়ারেন্টি ও ডেলিভারি এবং রিটার্ন ও রিফান্ড পেজ দেখুন।

## যোগাযোগ
এই শর্তাবলি নিয়ে কোনো প্রশ্ন থাকলে পেজের নিচে দেওয়া নম্বরে কল বা হোয়াটসঅ্যাপ করুন।""",
        "order": 5,
    },
]
