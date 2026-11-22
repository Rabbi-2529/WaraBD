"""Bangladesh districts with their thanas / upazilas (English, বাংলা).

Used once to fill the District and Thana tables (migration 0020). After
that the lists live in the database and are edited in the admin
(Website Content → Delivery charges), where missing thanas can be added.

"S" stands for "<district> Sadar" (e.g. "Gazipur Sadar" / "গাজীপুর সদর").
"""

DIVISIONS = {
    "Dhaka": "ঢাকা", "Chattogram": "চট্টগ্রাম", "Rajshahi": "রাজশাহী", "Khulna": "খুলনা",
    "Barishal": "বরিশাল", "Sylhet": "সিলেট", "Rangpur": "রংপুর", "Mymensingh": "ময়মনসিংহ",
}

# (district_en, district_bn, division, [ (thana_en, thana_bn) | "S" ])
DISTRICTS = [
    # ---------------------------------------------------------------- Dhaka division
    ("Dhaka", "ঢাকা", "Dhaka", [
        ("Adabor", "আদাবর"), ("Badda", "বাড্ডা"), ("Banani", "বনানী"), ("Bangshal", "বংশাল"),
        ("Bhashantek", "ভাসানটেক"), ("Bimanbandar", "বিমানবন্দর"), ("Cantonment", "ক্যান্টনমেন্ট"),
        ("Chawkbazar", "চকবাজার"), ("Dakshinkhan", "দক্ষিণখান"), ("Darus Salam", "দারুস সালাম"),
        ("Demra", "ডেমরা"), ("Dhanmondi", "ধানমন্ডি"), ("Gendaria", "গেন্ডারিয়া"), ("Gulshan", "গুলশান"),
        ("Hatirjheel", "হাতিরঝিল"), ("Hazaribagh", "হাজারীবাগ"), ("Jatrabari", "যাত্রাবাড়ী"),
        ("Kadamtali", "কদমতলী"), ("Kafrul", "কাফরুল"), ("Kalabagan", "কলাবাগান"),
        ("Kamrangirchar", "কামরাঙ্গীরচর"), ("Khilgaon", "খিলগাঁও"), ("Khilkhet", "খিলক্ষেত"),
        ("Kotwali", "কোতোয়ালী"), ("Lalbagh", "লালবাগ"), ("Mirpur", "মিরপুর"), ("Mohammadpur", "মোহাম্মদপুর"),
        ("Motijheel", "মতিঝিল"), ("Mugda", "মুগদা"), ("New Market", "নিউ মার্কেট"), ("Pallabi", "পল্লবী"),
        ("Paltan", "পল্টন"), ("Ramna", "রমনা"), ("Rampura", "রামপুরা"), ("Rupnagar", "রূপনগর"),
        ("Sabujbagh", "সবুজবাগ"), ("Shah Ali", "শাহ আলী"), ("Shahbagh", "শাহবাগ"),
        ("Sher-e-Bangla Nagar", "শেরেবাংলা নগর"), ("Shyampur", "শ্যামপুর"), ("Sutrapur", "সূত্রাপুর"),
        ("Tejgaon", "তেজগাঁও"), ("Tejgaon Industrial Area", "তেজগাঁও শিল্পাঞ্চল"), ("Turag", "তুরাগ"),
        ("Uttara East", "উত্তরা পূর্ব"), ("Uttara West", "উত্তরা পশ্চিম"), ("Uttarkhan", "উত্তরখান"),
        ("Vatara", "ভাটারা"), ("Wari", "ওয়ারী"),
        ("Dhamrai", "ধামরাই"), ("Dohar", "দোহার"), ("Keraniganj", "কেরানীগঞ্জ"), ("Nawabganj", "নবাবগঞ্জ"),
        ("Savar", "সাভার"),
    ]),
    ("Faridpur", "ফরিদপুর", "Dhaka", [
        ("Alfadanga", "আলফাডাঙ্গা"), ("Bhanga", "ভাঙ্গা"), ("Boalmari", "বোয়ালমারী"),
        ("Charbhadrasan", "চরভদ্রাসন"), "S", ("Madhukhali", "মধুখালী"), ("Nagarkanda", "নগরকান্দা"),
        ("Sadarpur", "সদরপুর"), ("Saltha", "সালথা"),
    ]),
    ("Gazipur", "গাজীপুর", "Dhaka", [
        "S", ("Kaliakair", "কালিয়াকৈর"), ("Kaliganj", "কালীগঞ্জ"), ("Kapasia", "কাপাসিয়া"),
        ("Sreepur", "শ্রীপুর"), ("Tongi", "টঙ্গী"),
    ]),
    ("Gopalganj", "গোপালগঞ্জ", "Dhaka", [
        "S", ("Kashiani", "কাশিয়ানী"), ("Kotalipara", "কোটালীপাড়া"), ("Muksudpur", "মুকসুদপুর"),
        ("Tungipara", "টুঙ্গিপাড়া"),
    ]),
    ("Kishoreganj", "কিশোরগঞ্জ", "Dhaka", [
        ("Austagram", "অষ্টগ্রাম"), ("Bajitpur", "বাজিতপুর"), ("Bhairab", "ভৈরব"), ("Hossainpur", "হোসেনপুর"),
        ("Itna", "ইটনা"), ("Karimganj", "করিমগঞ্জ"), ("Katiadi", "কটিয়াদী"), "S", ("Kuliarchar", "কুলিয়ারচর"),
        ("Mithamain", "মিঠামইন"), ("Nikli", "নিকলী"), ("Pakundia", "পাকুন্দিয়া"), ("Tarail", "তাড়াইল"),
    ]),
    ("Madaripur", "মাদারীপুর", "Dhaka", [
        ("Dasar", "ডাসার"), ("Kalkini", "কালকিনি"), "S", ("Rajoir", "রাজৈর"), ("Shibchar", "শিবচর"),
    ]),
    ("Manikganj", "মানিকগঞ্জ", "Dhaka", [
        ("Daulatpur", "দৌলতপুর"), ("Ghior", "ঘিওর"), ("Harirampur", "হরিরামপুর"), "S",
        ("Saturia", "সাটুরিয়া"), ("Shivalaya", "শিবালয়"), ("Singair", "সিংগাইর"),
    ]),
    ("Munshiganj", "মুন্সীগঞ্জ", "Dhaka", [
        ("Gazaria", "গজারিয়া"), ("Lohajang", "লৌহজং"), "S", ("Sirajdikhan", "সিরাজদিখান"),
        ("Sreenagar", "শ্রীনগর"), ("Tongibari", "টংগিবাড়ী"),
    ]),
    ("Narayanganj", "নারায়ণগঞ্জ", "Dhaka", [
        ("Araihazar", "আড়াইহাজার"), ("Bandar", "বন্দর"), ("Fatullah", "ফতুল্লা"), "S",
        ("Rupganj", "রূপগঞ্জ"), ("Siddhirganj", "সিদ্ধিরগঞ্জ"), ("Sonargaon", "সোনারগাঁও"),
    ]),
    ("Narsingdi", "নরসিংদী", "Dhaka", [
        ("Belabo", "বেলাবো"), ("Monohardi", "মনোহরদী"), "S", ("Palash", "পলাশ"), ("Raipura", "রায়পুরা"),
        ("Shibpur", "শিবপুর"),
    ]),
    ("Rajbari", "রাজবাড়ী", "Dhaka", [
        ("Baliakandi", "বালিয়াকান্দি"), ("Goalanda", "গোয়ালন্দ"), ("Kalukhali", "কালুখালী"), ("Pangsha", "পাংশা"), "S",
    ]),
    ("Shariatpur", "শরীয়তপুর", "Dhaka", [
        ("Bhedarganj", "ভেদরগঞ্জ"), ("Damudya", "ডামুড্যা"), ("Gosairhat", "গোসাইরহাট"), ("Naria", "নড়িয়া"), "S",
        ("Zajira", "জাজিরা"),
    ]),
    ("Tangail", "টাঙ্গাইল", "Dhaka", [
        ("Basail", "বাসাইল"), ("Bhuapur", "ভুয়াপুর"), ("Delduar", "দেলদুয়ার"), ("Dhanbari", "ধনবাড়ী"),
        ("Ghatail", "ঘাটাইল"), ("Gopalpur", "গোপালপুর"), ("Kalihati", "কালিহাতী"), ("Madhupur", "মধুপুর"),
        ("Mirzapur", "মির্জাপুর"), ("Nagarpur", "নাগরপুর"), ("Sakhipur", "সখিপুর"), "S",
    ]),
    # ---------------------------------------------------------------- Mymensingh division
    ("Jamalpur", "জামালপুর", "Mymensingh", [
        ("Bakshiganj", "বকশীগঞ্জ"), ("Dewanganj", "দেওয়ানগঞ্জ"), ("Islampur", "ইসলামপুর"), "S",
        ("Madarganj", "মাদারগঞ্জ"), ("Melandaha", "মেলান্দহ"), ("Sarishabari", "সরিষাবাড়ী"),
    ]),
    ("Mymensingh", "ময়মনসিংহ", "Mymensingh", [
        ("Bhaluka", "ভালুকা"), ("Dhobaura", "ধোবাউড়া"), ("Fulbaria", "ফুলবাড়িয়া"), ("Gaffargaon", "গফরগাঁও"),
        ("Gauripur", "গৌরীপুর"), ("Haluaghat", "হালুয়াঘাট"), ("Ishwarganj", "ঈশ্বরগঞ্জ"),
        ("Muktagachha", "মুক্তাগাছা"), "S", ("Nandail", "নান্দাইল"), ("Phulpur", "ফুলপুর"),
        ("Tarakanda", "তারাকান্দা"), ("Trishal", "ত্রিশাল"),
    ]),
    ("Netrokona", "নেত্রকোণা", "Mymensingh", [
        ("Atpara", "আটপাড়া"), ("Barhatta", "বারহাট্টা"), ("Durgapur", "দুর্গাপুর"), ("Kalmakanda", "কলমাকান্দা"),
        ("Kendua", "কেন্দুয়া"), ("Khaliajuri", "খালিয়াজুরী"), ("Madan", "মদন"), ("Mohanganj", "মোহনগঞ্জ"), "S",
        ("Purbadhala", "পূর্বধলা"),
    ]),
    ("Sherpur", "শেরপুর", "Mymensingh", [
        ("Jhenaigati", "ঝিনাইগাতী"), ("Nakla", "নকলা"), ("Nalitabari", "নালিতাবাড়ী"), "S", ("Sreebardi", "শ্রীবরদী"),
    ]),
    # ---------------------------------------------------------------- Chattogram division
    ("Bandarban", "বান্দরবান", "Chattogram", [
        ("Ali Kadam", "আলীকদম"), "S", ("Lama", "লামা"), ("Naikhongchhari", "নাইক্ষ্যংছড়ি"),
        ("Rowangchhari", "রোয়াংছড়ি"), ("Ruma", "রুমা"), ("Thanchi", "থানচি"),
    ]),
    ("Brahmanbaria", "ব্রাহ্মণবাড়িয়া", "Chattogram", [
        ("Akhaura", "আখাউড়া"), ("Ashuganj", "আশুগঞ্জ"), ("Bancharampur", "বাঞ্ছারামপুর"), ("Bijoynagar", "বিজয়নগর"), "S",
        ("Kasba", "কসবা"), ("Nabinagar", "নবীনগর"), ("Nasirnagar", "নাসিরনগর"), ("Sarail", "সরাইল"),
    ]),
    ("Chandpur", "চাঁদপুর", "Chattogram", [
        "S", ("Faridganj", "ফরিদগঞ্জ"), ("Haimchar", "হাইমচর"), ("Hajiganj", "হাজীগঞ্জ"), ("Kachua", "কচুয়া"),
        ("Matlab Dakshin", "মতলব দক্ষিণ"), ("Matlab Uttar", "মতলব উত্তর"), ("Shahrasti", "শাহরাস্তি"),
    ]),
    ("Chattogram", "চট্টগ্রাম", "Chattogram", [
        ("Akbar Shah", "আকবর শাহ"), ("Bakalia", "বাকলিয়া"), ("Bayazid Bostami", "বায়েজিদ বোস্তামী"),
        ("Bandar", "বন্দর"), ("Chandgaon", "চান্দগাঁও"), ("Chawkbazar", "চকবাজার"), ("Double Mooring", "ডবলমুরিং"),
        ("EPZ", "ইপিজেড"), ("Halishahar", "হালিশহর"), ("Khulshi", "খুলশী"), ("Kotwali", "কোতোয়ালী"),
        ("Pahartali", "পাহাড়তলী"), ("Panchlaish", "পাঁচলাইশ"), ("Patenga", "পতেঙ্গা"), ("Sadarghat", "সদরঘাট"),
        ("Anwara", "আনোয়ারা"), ("Banshkhali", "বাঁশখালী"), ("Boalkhali", "বোয়ালখালী"), ("Chandanaish", "চন্দনাইশ"),
        ("Fatikchhari", "ফটিকছড়ি"), ("Hathazari", "হাটহাজারী"), ("Karnaphuli", "কর্ণফুলী"), ("Lohagara", "লোহাগাড়া"),
        ("Mirsharai", "মীরসরাই"), ("Patiya", "পটিয়া"), ("Rangunia", "রাঙ্গুনিয়া"), ("Raozan", "রাউজান"),
        ("Sandwip", "সন্দ্বীপ"), ("Satkania", "সাতকানিয়া"), ("Sitakunda", "সীতাকুণ্ড"),
    ]),
    ("Cox's Bazar", "কক্সবাজার", "Chattogram", [
        ("Chakaria", "চকরিয়া"), "S", ("Eidgaon", "ঈদগাঁও"), ("Kutubdia", "কুতুবদিয়া"), ("Maheshkhali", "মহেশখালী"),
        ("Pekua", "পেকুয়া"), ("Ramu", "রামু"), ("Teknaf", "টেকনাফ"), ("Ukhia", "উখিয়া"),
    ]),
    ("Cumilla", "কুমিল্লা", "Chattogram", [
        ("Barura", "বরুড়া"), ("Brahmanpara", "ব্রাহ্মণপাড়া"), ("Burichang", "বুড়িচং"), ("Chandina", "চান্দিনা"),
        ("Chauddagram", "চৌদ্দগ্রাম"), ("Cumilla Adarsha Sadar", "কুমিল্লা আদর্শ সদর"),
        ("Cumilla Sadar Dakshin", "কুমিল্লা সদর দক্ষিণ"), ("Daudkandi", "দাউদকান্দি"), ("Debidwar", "দেবিদ্বার"),
        ("Homna", "হোমনা"), ("Laksam", "লাকসাম"), ("Lalmai", "লালমাই"), ("Manoharganj", "মনোহরগঞ্জ"),
        ("Meghna", "মেঘনা"), ("Muradnagar", "মুরাদনগর"), ("Nangalkot", "নাঙ্গলকোট"), ("Titas", "তিতাস"),
    ]),
    ("Feni", "ফেনী", "Chattogram", [
        ("Chhagalnaiya", "ছাগলনাইয়া"), ("Daganbhuiyan", "দাগনভূঞা"), "S", ("Fulgazi", "ফুলগাজী"),
        ("Parshuram", "পরশুরাম"), ("Sonagazi", "সোনাগাজী"),
    ]),
    ("Khagrachhari", "খাগড়াছড়ি", "Chattogram", [
        ("Dighinala", "দীঘিনালা"), ("Guimara", "গুইমারা"), "S", ("Lakshmichhari", "লক্ষ্মীছড়ি"),
        ("Mahalchhari", "মহালছড়ি"), ("Manikchhari", "মানিকছড়ি"), ("Matiranga", "মাটিরাঙ্গা"),
        ("Panchhari", "পানছড়ি"), ("Ramgarh", "রামগড়"),
    ]),
    ("Lakshmipur", "লক্ষ্মীপুর", "Chattogram", [
        ("Kamalnagar", "কমলনগর"), "S", ("Raipur", "রায়পুর"), ("Ramganj", "রামগঞ্জ"), ("Ramgati", "রামগতি"),
    ]),
    ("Noakhali", "নোয়াখালী", "Chattogram", [
        ("Begumganj", "বেগমগঞ্জ"), ("Chatkhil", "চাটখিল"), ("Companiganj", "কোম্পানীগঞ্জ"), ("Hatiya", "হাতিয়া"),
        ("Kabirhat", "কবিরহাট"), "S", ("Senbagh", "সেনবাগ"), ("Sonaimuri", "সোনাইমুড়ী"), ("Subarnachar", "সুবর্ণচর"),
    ]),
    ("Rangamati", "রাঙ্গামাটি", "Chattogram", [
        ("Baghaichhari", "বাঘাইছড়ি"), ("Barkal", "বরকল"), ("Belaichhari", "বিলাইছড়ি"), ("Juraichhari", "জুরাছড়ি"),
        ("Kaptai", "কাপ্তাই"), ("Kawkhali", "কাউখালী"), ("Langadu", "লংগদু"), ("Naniarchar", "নানিয়ারচর"),
        ("Rajasthali", "রাজস্থলী"), "S",
    ]),
    # ---------------------------------------------------------------- Rajshahi division
    ("Bogura", "বগুড়া", "Rajshahi", [
        ("Adamdighi", "আদমদীঘি"), "S", ("Dhunat", "ধুনট"), ("Dhupchanchia", "দুপচাঁচিয়া"), ("Gabtali", "গাবতলী"),
        ("Kahaloo", "কাহালু"), ("Nandigram", "নন্দীগ্রাম"), ("Sariakandi", "সারিয়াকান্দি"), ("Shajahanpur", "শাজাহানপুর"),
        ("Sherpur", "শেরপুর"), ("Shibganj", "শিবগঞ্জ"), ("Sonatala", "সোনাতলা"),
    ]),
    ("Chapai Nawabganj", "চাঁপাইনবাবগঞ্জ", "Rajshahi", [
        ("Bholahat", "ভোলাহাট"), "S", ("Gomastapur", "গোমস্তাপুর"), ("Nachole", "নাচোল"), ("Shibganj", "শিবগঞ্জ"),
    ]),
    ("Joypurhat", "জয়পুরহাট", "Rajshahi", [
        ("Akkelpur", "আক্কেলপুর"), "S", ("Kalai", "কালাই"), ("Khetlal", "ক্ষেতলাল"), ("Panchbibi", "পাঁচবিবি"),
    ]),
    ("Naogaon", "নওগাঁ", "Rajshahi", [
        ("Atrai", "আত্রাই"), ("Badalgachhi", "বদলগাছী"), ("Dhamoirhat", "ধামইরহাট"), ("Mahadebpur", "মহাদেবপুর"),
        ("Manda", "মান্দা"), "S", ("Niamatpur", "নিয়ামতপুর"), ("Patnitala", "পত্নীতলা"), ("Porsha", "পোরশা"),
        ("Raninagar", "রাণীনগর"), ("Sapahar", "সাপাহার"),
    ]),
    ("Natore", "নাটোর", "Rajshahi", [
        ("Bagatipara", "বাগাতিপাড়া"), ("Baraigram", "বড়াইগ্রাম"), ("Gurudaspur", "গুরুদাসপুর"), ("Lalpur", "লালপুর"),
        ("Naldanga", "নলডাঙ্গা"), "S", ("Singra", "সিংড়া"),
    ]),
    ("Pabna", "পাবনা", "Rajshahi", [
        ("Atgharia", "আটঘরিয়া"), ("Bera", "বেড়া"), ("Bhangura", "ভাঙ্গুড়া"), ("Chatmohar", "চাটমোহর"),
        ("Faridpur", "ফরিদপুর"), ("Ishwardi", "ঈশ্বরদী"), "S", ("Santhia", "সাঁথিয়া"), ("Sujanagar", "সুজানগর"),
    ]),
    ("Rajshahi", "রাজশাহী", "Rajshahi", [
        ("Boalia", "বোয়ালিয়া"), ("Motihar", "মতিহার"), ("Rajpara", "রাজপাড়া"), ("Shah Makhdum", "শাহ মখদুম"),
        ("Bagha", "বাঘা"), ("Bagmara", "বাগমারা"), ("Charghat", "চারঘাট"), ("Durgapur", "দুর্গাপুর"),
        ("Godagari", "গোদাগাড়ী"), ("Mohanpur", "মোহনপুর"), ("Paba", "পবা"), ("Puthia", "পুঠিয়া"), ("Tanore", "তানোর"),
    ]),
    ("Sirajganj", "সিরাজগঞ্জ", "Rajshahi", [
        ("Belkuchi", "বেলকুচি"), ("Chauhali", "চৌহালি"), ("Kamarkhanda", "কামারখন্দ"), ("Kazipur", "কাজীপুর"),
        ("Raiganj", "রায়গঞ্জ"), ("Shahjadpur", "শাহজাদপুর"), "S", ("Tarash", "তাড়াশ"), ("Ullahpara", "উল্লাপাড়া"),
    ]),
    # ---------------------------------------------------------------- Rangpur division
    ("Dinajpur", "দিনাজপুর", "Rangpur", [
        ("Birampur", "বিরামপুর"), ("Birganj", "বীরগঞ্জ"), ("Biral", "বিরল"), ("Bochaganj", "বোচাগঞ্জ"),
        ("Chirirbandar", "চিরিরবন্দর"), "S", ("Fulbari", "ফুলবাড়ী"), ("Ghoraghat", "ঘোড়াঘাট"), ("Hakimpur", "হাকিমপুর"),
        ("Kaharole", "কাহারোল"), ("Khansama", "খানসামা"), ("Nawabganj", "নবাবগঞ্জ"), ("Parbatipur", "পার্বতীপুর"),
    ]),
    ("Gaibandha", "গাইবান্ধা", "Rangpur", [
        ("Fulchhari", "ফুলছড়ি"), "S", ("Gobindaganj", "গোবিন্দগঞ্জ"), ("Palashbari", "পলাশবাড়ী"),
        ("Sadullapur", "সাদুল্লাপুর"), ("Saghata", "সাঘাটা"), ("Sundarganj", "সুন্দরগঞ্জ"),
    ]),
    ("Kurigram", "কুড়িগ্রাম", "Rangpur", [
        ("Bhurungamari", "ভুরুঙ্গামারী"), ("Char Rajibpur", "চর রাজিবপুর"), ("Chilmari", "চিলমারী"), "S",
        ("Nageshwari", "নাগেশ্বরী"), ("Phulbari", "ফুলবাড়ী"), ("Rajarhat", "রাজারহাট"), ("Raumari", "রৌমারী"),
        ("Ulipur", "উলিপুর"),
    ]),
    ("Lalmonirhat", "লালমনিরহাট", "Rangpur", [
        ("Aditmari", "আদিতমারী"), ("Hatibandha", "হাতীবান্ধা"), ("Kaliganj", "কালীগঞ্জ"), "S", ("Patgram", "পাটগ্রাম"),
    ]),
    ("Nilphamari", "নীলফামারী", "Rangpur", [
        ("Dimla", "ডিমলা"), ("Domar", "ডোমার"), ("Jaldhaka", "জলঢাকা"), ("Kishoreganj", "কিশোরগঞ্জ"), "S",
        ("Saidpur", "সৈয়দপুর"),
    ]),
    ("Panchagarh", "পঞ্চগড়", "Rangpur", [
        ("Atwari", "আটোয়ারী"), ("Boda", "বোদা"), ("Debiganj", "দেবীগঞ্জ"), "S", ("Tetulia", "তেঁতুলিয়া"),
    ]),
    ("Rangpur", "রংপুর", "Rangpur", [
        ("Badarganj", "বদরগঞ্জ"), ("Gangachara", "গংগাচড়া"), ("Kaunia", "কাউনিয়া"), ("Mithapukur", "মিঠাপুকুর"),
        ("Pirgachha", "পীরগাছা"), ("Pirganj", "পীরগঞ্জ"), "S", ("Taraganj", "তারাগঞ্জ"),
    ]),
    ("Thakurgaon", "ঠাকুরগাঁও", "Rangpur", [
        ("Baliadangi", "বালিয়াডাঙ্গী"), ("Haripur", "হরিপুর"), ("Pirganj", "পীরগঞ্জ"), ("Ranisankail", "রাণীশংকৈল"), "S",
    ]),
    # ---------------------------------------------------------------- Khulna division
    ("Bagerhat", "বাগেরহাট", "Khulna", [
        "S", ("Chitalmari", "চিতলমারী"), ("Fakirhat", "ফকিরহাট"), ("Kachua", "কচুয়া"), ("Mollahat", "মোল্লাহাট"),
        ("Mongla", "মোংলা"), ("Morrelganj", "মোরেলগঞ্জ"), ("Rampal", "রামপাল"), ("Sarankhola", "শরণখোলা"),
    ]),
    ("Chuadanga", "চুয়াডাঙ্গা", "Khulna", [
        ("Alamdanga", "আলমডাঙ্গা"), "S", ("Damurhuda", "দামুড়হুদা"), ("Jibannagar", "জীবননগর"),
    ]),
    ("Jashore", "যশোর", "Khulna", [
        ("Abhaynagar", "অভয়নগর"), ("Bagherpara", "বাঘারপাড়া"), ("Chaugachha", "চৌগাছা"), ("Jhikargachha", "ঝিকরগাছা"),
        "S", ("Keshabpur", "কেশবপুর"), ("Manirampur", "মণিরামপুর"), ("Sharsha", "শার্শা"),
    ]),
    ("Jhenaidah", "ঝিনাইদহ", "Khulna", [
        ("Harinakunda", "হরিণাকুণ্ডু"), "S", ("Kaliganj", "কালীগঞ্জ"), ("Kotchandpur", "কোটচাঁদপুর"),
        ("Maheshpur", "মহেশপুর"), ("Shailkupa", "শৈলকুপা"),
    ]),
    ("Khulna", "খুলনা", "Khulna", [
        ("Daulatpur", "দৌলতপুর"), ("Khalishpur", "খালিশপুর"), ("Khan Jahan Ali", "খান জাহান আলী"),
        ("Sonadanga", "সোনাডাঙ্গা"), "S", ("Batiaghata", "বটিয়াঘাটা"), ("Dacope", "দাকোপ"), ("Dighalia", "দিঘলিয়া"),
        ("Dumuria", "ডুমুরিয়া"), ("Koyra", "কয়রা"), ("Paikgachha", "পাইকগাছা"), ("Phultala", "ফুলতলা"),
        ("Rupsa", "রূপসা"), ("Terokhada", "তেরখাদা"),
    ]),
    ("Kushtia", "কুষ্টিয়া", "Khulna", [
        ("Bheramara", "ভেড়ামারা"), ("Daulatpur", "দৌলতপুর"), ("Khoksa", "খোকসা"), ("Kumarkhali", "কুমারখালী"), "S",
        ("Mirpur", "মিরপুর"),
    ]),
    ("Magura", "মাগুরা", "Khulna", [
        "S", ("Mohammadpur", "মহম্মদপুর"), ("Shalikha", "শালিখা"), ("Sreepur", "শ্রীপুর"),
    ]),
    ("Meherpur", "মেহেরপুর", "Khulna", [
        ("Gangni", "গাংনী"), "S", ("Mujibnagar", "মুজিবনগর"),
    ]),
    ("Narail", "নড়াইল", "Khulna", [
        ("Kalia", "কালিয়া"), ("Lohagara", "লোহাগড়া"), "S",
    ]),
    ("Satkhira", "সাতক্ষীরা", "Khulna", [
        ("Assasuni", "আশাশুনি"), ("Debhata", "দেবহাটা"), ("Kalaroa", "কলারোয়া"), ("Kaliganj", "কালীগঞ্জ"), "S",
        ("Shyamnagar", "শ্যামনগর"), ("Tala", "তালা"),
    ]),
    # ---------------------------------------------------------------- Barishal division
    ("Barguna", "বরগুনা", "Barishal", [
        ("Amtali", "আমতলী"), ("Bamna", "বামনা"), "S", ("Betagi", "বেতাগী"), ("Patharghata", "পাথরঘাটা"),
        ("Taltali", "তালতলী"),
    ]),
    ("Barishal", "বরিশাল", "Barishal", [
        ("Agailjhara", "আগৈলঝাড়া"), ("Babuganj", "বাবুগঞ্জ"), ("Bakerganj", "বাকেরগঞ্জ"), ("Banaripara", "বানারীপাড়া"),
        "S", ("Gournadi", "গৌরনদী"), ("Hizla", "হিজলা"), ("Mehendiganj", "মেহেন্দিগঞ্জ"), ("Muladi", "মুলাদী"),
        ("Wazirpur", "উজিরপুর"),
    ]),
    ("Bhola", "ভোলা", "Barishal", [
        "S", ("Burhanuddin", "বোরহানউদ্দিন"), ("Char Fasson", "চরফ্যাশন"), ("Daulatkhan", "দৌলতখান"),
        ("Lalmohan", "লালমোহন"), ("Manpura", "মনপুরা"), ("Tazumuddin", "তজুমদ্দিন"),
    ]),
    ("Jhalokathi", "ঝালকাঠি", "Barishal", [
        "S", ("Kathalia", "কাঠালিয়া"), ("Nalchity", "নলছিটি"), ("Rajapur", "রাজাপুর"),
    ]),
    ("Patuakhali", "পটুয়াখালী", "Barishal", [
        ("Bauphal", "বাউফল"), ("Dashmina", "দশমিনা"), ("Dumki", "দুমকি"), ("Galachipa", "গলাচিপা"),
        ("Kalapara", "কলাপাড়া"), ("Mirzaganj", "মির্জাগঞ্জ"), "S", ("Rangabali", "রাঙ্গাবালী"),
    ]),
    ("Pirojpur", "পিরোজপুর", "Barishal", [
        ("Bhandaria", "ভান্ডারিয়া"), ("Indurkani", "ইন্দুরকানী"), ("Kawkhali", "কাউখালী"), ("Mathbaria", "মঠবাড়িয়া"),
        ("Nazirpur", "নাজিরপুর"), ("Nesarabad", "নেছারাবাদ"), "S",
    ]),
    # ---------------------------------------------------------------- Sylhet division
    ("Habiganj", "হবিগঞ্জ", "Sylhet", [
        ("Ajmiriganj", "আজমিরীগঞ্জ"), ("Bahubal", "বাহুবল"), ("Baniachong", "বানিয়াচং"), ("Chunarughat", "চুনারুঘাট"),
        "S", ("Lakhai", "লাখাই"), ("Madhabpur", "মাধবপুর"), ("Nabiganj", "নবীগঞ্জ"), ("Shayestaganj", "শায়েস্তাগঞ্জ"),
    ]),
    ("Moulvibazar", "মৌলভীবাজার", "Sylhet", [
        ("Barlekha", "বড়লেখা"), ("Juri", "জুড়ী"), ("Kamalganj", "কমলগঞ্জ"), ("Kulaura", "কুলাউড়া"), "S",
        ("Rajnagar", "রাজনগর"), ("Sreemangal", "শ্রীমঙ্গল"),
    ]),
    ("Sunamganj", "সুনামগঞ্জ", "Sylhet", [
        ("Bishwambharpur", "বিশ্বম্ভরপুর"), ("Chhatak", "ছাতক"), ("Derai", "দিরাই"), ("Dharamapasha", "ধর্মপাশা"),
        ("Doarabazar", "দোয়ারাবাজার"), ("Jagannathpur", "জগন্নাথপুর"), ("Jamalganj", "জামালগঞ্জ"),
        ("Madhyanagar", "মধ্যনগর"), ("Shalla", "শাল্লা"), ("Shantiganj", "শান্তিগঞ্জ"), "S", ("Tahirpur", "তাহিরপুর"),
    ]),
    ("Sylhet", "সিলেট", "Sylhet", [
        ("Balaganj", "বালাগঞ্জ"), ("Beanibazar", "বিয়ানীবাজার"), ("Bishwanath", "বিশ্বনাথ"), ("Companiganj", "কোম্পানীগঞ্জ"),
        ("Dakshin Surma", "দক্ষিণ সুরমা"), ("Fenchuganj", "ফেঞ্চুগঞ্জ"), ("Golapganj", "গোলাপগঞ্জ"),
        ("Gowainghat", "গোয়াইনঘাট"), ("Jaintiapur", "জৈন্তাপুর"), ("Kanaighat", "কানাইঘাট"),
        ("Osmani Nagar", "ওসমানী নগর"), "S", ("Zakiganj", "জকিগঞ্জ"),
    ]),
]


def expanded():
    """[(district_en, district_bn, division, [(thana_en, thana_bn), ...])] with "S" expanded."""
    rows = []
    for d_en, d_bn, division, thanas in DISTRICTS:
        items = []
        for t in thanas:
            items.append((f"{d_en} Sadar", f"{d_bn} সদর") if t == "S" else t)
        rows.append((d_en, d_bn, division, items))
    return rows
