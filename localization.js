(() => {
    const translations = {
        'Lamu Tours': 'Lamu Tours',
        'Home': 'Mwanzo',
        'Tours': 'Ziara',
        'Booking': 'Uhifadhi',
        'About Lamu': 'Kuhusu Lamu',
        'Contact': 'Wasiliana Nasi',
        'Hospitality': 'Malazi',
        'Sign in / Register': 'Ingia / Jisajili',
        'Switch to Kiswahili': 'Badilisha hadi Kiswahili',
        'Switch to English': 'Badilisha hadi Kiingereza',
        'or': 'au',
        'Duration: Half day': 'Muda: Nusu siku',
        'Duration: 3 hours': 'Muda: Saa 3',
        'Duration: Full day': 'Muda: Siku nzima',
        'Duration: 4 hours': 'Muda: Saa 4',
        'Price:': 'Bei:',
        'Welcome Back to Lamu - Lamu Tours': 'Karibu Tena Lamu - Lamu Tours',
        'Join the Lamu Experience - Lamu Tours': 'Jiunge na Matukio ya Lamu - Lamu Tours',
        'Plan Your Lamu Adventure - Lamu Tours': 'Panga Safari Yako ya Lamu - Lamu Tours',
        'Let’s Plan Your Lamu Escape - Lamu Tours': 'Tupange Safari Yako ya Lamu - Lamu Tours',
        'Discover the Story of Lamu - Lamu Tours': 'Gundua Historia ya Lamu - Lamu Tours',
        'Explore Lamu’s Most Memorable Tours': 'Gundua Ziara Zisizosahaulika za Lamu',
        'Find Your Perfect Lamu Stay - Lamu Tours': 'Pata Malazi Bora Lamu - Lamu Tours',
        'Your Lamu Tour, Up Close - Lamu Tours': 'Ijue Ziara Yako ya Lamu kwa Karibu - Lamu Tours',
        'Your Lamu Adventure Starts Here': 'Safari Yako ya Lamu Inaanzia Hapa',
        'Lamu Tours & Booking Agency': 'Lamu Tours na Shirika la Uhifadhi',
        'Discover Lamu: Tours, Stays & Island Experiences': 'Gundua Lamu: Ziara, Malazi na Matukio ya Kisiwa',
        'Explore Lamu’s Most Memorable Tours': 'Gundua Ziara Zisizosahaulika za Lamu',
        'Step Into the Story of Lamu': 'Ingia Katika Historia ya Lamu',
        'Let’s Plan Your Lamu Escape': 'Tupange Safari Yako ya Lamu',
        'Plan Your Lamu Adventure': 'Panga Safari Yako ya Lamu',
        'Find Your Perfect Lamu Stay': 'Pata Malazi Bora Lamu',
        'Your Lamu Tour, Up Close': 'Ijue Ziara Yako ya Lamu kwa Karibu',
        'Welcome Back to Lamu': 'Karibu Tena Lamu',
        'Join the Lamu Experience': 'Jiunge na Matukio ya Lamu',
        'Your Lamu Adventure Starts Here': 'Safari Yako ya Lamu Inaanzia Hapa',
        'Trending destinations around Lamu': 'Maeneo Maarufu Karibu na Lamu',
        'Discover popular coastal neighborhoods and find a hotel, apartment, villa, or home nearby.': 'Gundua maeneo maarufu ya pwani na upate hoteli, fleti, vila au nyumba karibu nawe.',
        'Find your place to stay': 'Pata Mahali pa Kukaa',
        'Search low prices on hotels, homes, guest houses and much more across Lamu.': 'Tafuta bei nafuu za hoteli, nyumba za wageni na mengine mengi kote Lamu.',
        'Where are you going?': 'Unaelekea wapi?',
        'Lamu, Shela or Manda': 'Lamu, Shela au Manda',
        'Lamu Island, Kenya': 'Kisiwa cha Lamu, Kenya',
        'Stay dates': 'Tarehe za kukaa',
        'Check-in': 'Kuingia',
        'Check-out': 'Kutoka',
        'Guests': 'Wageni',
        '1 guest': 'Mgeni 1',
        '2 guests': 'Wageni 2',
        '3 guests': 'Wageni 3',
        '4 guests': 'Wageni 4',
        '5+ guests': 'Wageni 5 au zaidi',
        'Stay type': 'Aina ya malazi',
        'Any type': 'Aina yoyote',
        'Hotels': 'Hoteli',
        'Homes': 'Nyumba',
        'Guest houses': 'Nyumba za wageni',
        'Villas': 'Vila',
        'Search stays': 'Tafuta Malazi',
        'Check-out must be after check-in.': 'Tarehe ya kutoka lazima iwe baada ya tarehe ya kuingia.',
        'Affordable stays in Lamu': 'Malazi Nafuu Lamu',
        '10 places found': 'Maeneo 10 yamepatikana',
        'Shela': 'Shela',
        'Lamu Old Town': 'Mji Mkongwe wa Lamu',
        'Manda Island': 'Kisiwa cha Manda',
        'Kipungani': 'Kipungani',
        'Lamu Mjini': 'Lamu Mjini',
        'Lamu Coast': 'Pwani ya Lamu',
        'Beach apartments and peaceful villas.': 'Fleti za ufukweni na vila tulivu.',
        'Swahili hotels close to history and culture.': 'Hoteli za Kiswahili karibu na historia na utamaduni.',
        'Ocean homes and spacious private villas.': 'Nyumba za kando ya bahari na vila pana za faragha.',
        'Quiet guest houses along the coast.': 'Nyumba tulivu za wageni kando ya pwani.',
        'Affordable city stays and apartments.': 'Malazi nafuu ya mjini na fleti.',
        'Waterfront escapes for every kind of traveler.': 'Mapumziko kando ya maji kwa kila aina ya msafiri.',
        'Shela Village Guest House': 'Nyumba ya Wageni ya Shela Village',
        'Old Town Swahili Hotel': 'Hoteli ya Kiswahili ya Mji Mkongwe',
        'Manda Island Beach Home': 'Nyumba ya Ufukweni ya Kisiwa cha Manda',
        'Shela Palm Villa': 'Vila ya Shela Palm',
        'Lamu Mjini Budget Hotel': 'Hoteli Nafuu ya Lamu Mjini',
        'Kipungani Coast Guest House': 'Nyumba ya Wageni ya Pwani ya Kipungani',
        'Manda Ocean Villa': 'Vila ya Bahari ya Manda',
        'Guest house · Shela': 'Nyumba ya wageni · Shela',
        'Hotel · Lamu Old Town': 'Hoteli · Mji Mkongwe wa Lamu',
        'Entire home · Manda': 'Nyumba nzima · Manda',
        'Villa · Shela': 'Vila · Shela',
        'Hotel · Lamu Mjini': 'Hoteli · Lamu Mjini',
        'Guest house · Kipungani': 'Nyumba ya wageni · Kipungani',
        'Villa · Manda': 'Vila · Manda',
        'From ': 'Kuanzia ',
        ' / night': ' / usiku',
        'places found': 'maeneo yamepatikana',
        'place found': 'mahali pamepatikana',
        'Find stays': 'Tafuta Malazi',
        'Book this stay': 'Hifadhi Malazi Haya',
        'View property': 'Tazama Makazi',
        'From': 'Kuanzia',
        'No stays match those details. Try Lamu, Shela or Manda.': 'Hakuna malazi yanayolingana na maelezo hayo. Jaribu Lamu, Shela au Manda.',
        'Our Services': 'Huduma Zetu',
        'Tour Packages': 'Vifurushi vya Ziara',
        'Hotel Bookings': 'Uhifadhi wa Hoteli',
        'Transportation': 'Usafiri',
        'Custom Itineraries': 'Ratiba Maalum za Safari',
        'About Us': 'Kuhusu Sisi',
        'Discover the beauty of Lamu with our expert-guided tours and seamless booking services. Explore historical sites, pristine beaches, and cultural experiences.': 'Gundua uzuri wa Lamu kupitia ziara zinazoongozwa na wataalamu na huduma rahisi za uhifadhi. Tembelea maeneo ya kihistoria, fukwe safi na matukio ya kitamaduni.',
        'Available Tours': 'Ziara Zinazopatikana',
        'Explore the Lamu Coast': 'Gundua Pwani ya Lamu',
        'See the beaches, boats, villages, and island landscapes waiting beyond the next tour.': 'Tazama fukwe, mashua, vijiji na mandhari ya visiwa katika ziara yako ijayo.',
        'Turquoise coastal waters': 'Maji ya pwani ya samawati',
        'Quiet island beaches': 'Fukwe tulivu za kisiwa',
        'Dhow sailing routes': 'Njia za safari za jahazi',
        'Stay beside the sea': 'Kaa kando ya bahari',
        'Island horizons': 'Mandhari ya visiwa',
        'Waterfront life': 'Maisha kando ya maji',
        'Sandbank escapes': 'Mapumziko kwenye fungu la mchanga',
        'Sunset on the coast': 'Machweo ya jua pwani',
        'Traditional dhow boats': 'Majaribu ya jadi',
        'Shoreline walks': 'Matembezi ufukweni',
        'Open ocean views': 'Mandhari ya bahari wazi',
        'Coastal village life': 'Maisha ya kijiji cha pwani',
        'Dhow Trips': 'Safari za Jahazi',
        'Enjoy traditional dhow sailing around Lamu\'s coastline with snorkeling and island stops.': 'Furahia safari ya jahazi la jadi kuzunguka pwani ya Lamu, kwa kuogelea chini ya maji na kutembelea visiwa.',
        'Enjoy traditional dhow sailing around Lamu’s coastline with snorkeling and island stops.': 'Furahia safari ya jahazi la jadi kuzunguka pwani ya Lamu, kwa kuogelea chini ya maji na kutembelea visiwa.',
        'Old Town Walks': 'Matembezi Mji Mkongwe',
        'Explore the historic streets, architecture, and marketplaces of Lamu Old Town.': 'Gundua mitaa ya kihistoria, usanifu majengo na masoko ya Mji Mkongwe wa Lamu.',
        'Sandbank Picnics': 'Pikiniki kwenye Fungu la Mchanga',
        'Relax on a private sandbank with picnic lunch, swimming, and beach activities.': 'Pumzika kwenye fungu la mchanga la faragha, furahia chakula cha mchana, kuogelea na shughuli za ufukweni.',
        'Fishing Trips': 'Safari za Uvuvi',
        'Go deep-sea fishing with local crew and enjoy fresh catch barbecue.': 'Nenda kuvua samaki bahari kuu na wafanyakazi wa eneo hili, kisha ufurahie samaki wabichi wa kuchoma.',
        'Water Sports': 'Michezo ya Majini',
        'Experience adrenaline with jet skiing, windsurfing, and paddleboarding in clear waters.': 'Furahia msisimko wa kuteleza kwa ndege ya majini, kutumia ubao wa upepo na kupiga makasia kwenye maji safi.',
        'Day Trips': 'Safari za Siku Moja',
        'Explore nearby islands and coastal attractions on a full-day guided excursion.': 'Gundua visiwa vya karibu na vivutio vya pwani katika safari ya siku nzima inayoongozwa.',
        'Cultural Tours': 'Ziara za Kitamaduni',
        'Visit museums, traditional workshops, and attend local cultural performances.': 'Tembelea makumbusho na karakana za jadi, na uhudhurie maonesho ya kitamaduni ya wenyeji.',
        'View Details': 'Tazama Maelezo',
        'Book Now': 'Hifadhi Sasa',
        'Shela Village Guest House - KSh 4,500/night': 'Nyumba ya Wageni ya Shela Village - KSh 4,500/usiku',
        'Old Town Swahili Hotel - KSh 6,500/night': 'Hoteli ya Kiswahili ya Mji Mkongwe - KSh 6,500/usiku',
        'Manda Island Beach Home - KSh 10,000/night': 'Nyumba ya Ufukweni ya Kisiwa cha Manda - KSh 10,000/usiku',
        'Shela Palm Villa - KSh 12,500/night': 'Vila ya Shela Palm - KSh 12,500/usiku',
        'Lamu Mjini Budget Hotel - KSh 5,500/night': 'Hoteli Nafuu ya Lamu Mjini - KSh 5,500/usiku',
        'Kipungani Coast Guest House - KSh 5,000/night': 'Nyumba ya Wageni ya Pwani ya Kipungani - KSh 5,000/usiku',
        'Manda Ocean Villa - KSh 16,000/night': 'Vila ya Bahari ya Manda - KSh 16,000/usiku',
        'Duration: Half day | Price: KSh 8,500 per person': 'Muda: Nusu siku | Bei: KSh 8,500 kwa mtu',
        'Duration: 3 hours | Price: KSh 3,500 per person': 'Muda: Saa 3 | Bei: KSh 3,500 kwa mtu',
        'Duration: Half day | Price: KSh 7,000 per person': 'Muda: Nusu siku | Bei: KSh 7,000 kwa mtu',
        'Duration: Full day | Price: KSh 12,000 per person': 'Muda: Siku nzima | Bei: KSh 12,000 kwa mtu',
        'Duration: Half day | Price: KSh 9,500 per person': 'Muda: Nusu siku | Bei: KSh 9,500 kwa mtu',
        'Duration: Full day | Price: KSh 9,000 per person': 'Muda: Siku nzima | Bei: KSh 9,000 kwa mtu',
        'Duration: 4 hours | Price: KSh 4,000 per person': 'Muda: Saa 4 | Bei: KSh 4,000 kwa mtu',
        'Half day': 'Nusu siku',
        '3 hours': 'Saa 3',
        'Full day': 'Siku nzima',
        '4 hours': 'Saa 4',
        'KSh 8,500 per person': 'KSh 8,500 kwa mtu',
        'KSh 3,500 per person': 'KSh 3,500 kwa mtu',
        'KSh 7,000 per person': 'KSh 7,000 kwa mtu',
        'KSh 12,000 per person': 'KSh 12,000 kwa mtu',
        'KSh 4,000 per person': 'KSh 4,000 kwa mtu',
        'KSh 9,500 per person': 'KSh 9,500 kwa mtu',
        'KSh 9,000 per person': 'KSh 9,000 kwa mtu',
        'Dhow ride, snorkeling gear, light refreshments': 'Safari ya jahazi, vifaa vya kuogelea chini ya maji na viburudisho',
        'Guided walk, cultural insights, local stories': 'Matembezi ya kuongozwa, maarifa ya kitamaduni na simulizi za wenyeji',
        'Boat transfer, picnic lunch, water activities': 'Usafiri wa mashua, chakula cha mchana cha pikiniki na shughuli za majini',
        'Fishing equipment, crew, catch cooking': 'Vifaa vya uvuvi, wafanyakazi na upishi wa samaki',
        'Guided cultural tour, entrance to local sites': 'Ziara ya kitamaduni ya kuongozwa na kiingilio kwenye maeneo ya wenyeji',
        'Equipment rental, instructor, safety brief': 'Ukodishaji wa vifaa, mwalimu na maelekezo ya usalama',
        'Boat transport, lunch, guide': 'Usafiri wa mashua, chakula cha mchana na mwongoza watalii',
        'Meet at the jetty': 'Kutana kwenye gati',
        'Sail to nearby islands': 'Safiri kwa jahazi hadi visiwa vya karibu',
        'Snorkeling stops': 'Vituo vya kuogelea chini ya maji',
        'Beach relaxation': 'Mapumziko ufukweni',
        'Return at sunset': 'Rudi wakati wa machweo',
        'Meet at agency office': 'Kutana katika ofisi ya shirika',
        'Walk through narrow lanes': 'Tembea kwenye vichochoro vyembamba',
        'Visit mosques and museums': 'Tembelea misikiti na makumbusho',
        'Local art and crafts market': 'Soko la sanaa na ufundi wa wenyeji',
        'Return': 'Rudi',
        'Depart by boat': 'Ondoka kwa mashua',
        'Arrive at sandbank': 'Fika kwenye fungu la mchanga',
        'Picnic lunch': 'Chakula cha mchana cha pikiniki',
        'Swimming and sunbathing': 'Kuogelea na kuota jua',
        'Return to Lamu': 'Rudi Lamu',
        'Meet at pier': 'Kutana kwenye gati',
        'Head to deep-sea fishing spot': 'Elekea eneo la uvuvi wa bahari kuu',
        'Fishing session': 'Kipindi cha uvuvi',
        'Cook fresh catch on board': 'Pika samaki wabichi ndani ya mashua',
        'Visit Lamu Museum': 'Tembelea Makumbusho ya Lamu',
        'Traditional Swahili home visit': 'Tembelea nyumba ya jadi ya Waswahili',
        'Cultural performance': 'Maonesho ya kitamaduni',
        'Local crafts demonstration': 'Onesho la ufundi wa wenyeji',
        'Wrap-up': 'Hitimisho',
        'Meet at beach jetty': 'Kutana kwenye gati la ufukweni',
        'Safety briefing': 'Maelekezo ya usalama',
        'Jet ski session': 'Kipindi cha kuteleza kwa ndege ya majini',
        'Windsurfing/paddleboarding': 'Kutumia ubao wa upepo/kupiga makasia',
        'Relax on beach': 'Pumzika ufukweni',
        'Visit nearby island': 'Tembelea kisiwa cha karibu',
        'Lunch and beach time': 'Chakula cha mchana na muda wa ufukweni',
        'Coastal sightseeing': 'Kutalii pwani',
        'About Lamu': 'Kuhusu Lamu',
        'History': 'Historia',
        'Culture': 'Utamaduni',
        'Attractions': 'Vivutio',
        'Beaches': 'Fukwe',
        'Museums & Cultural Sites': 'Makumbusho na Maeneo ya Utamaduni',
        'Donkey Sanctuary': 'Hifadhi ya Punda',
        'Traditional Living': 'Maisha ya Jadi',
        'Local Transport & Living': 'Usafiri na Maisha ya Wenyeji',
        'Visit Lamu to experience a piece of living history and immerse yourself in its timeless charm.': 'Tembelea Lamu ujionee historia hai na uzame katika mvuto wake usio na kifani.',
        'Lamu is a small island located off the coast of Kenya, known for its rich history, stunning architecture, and vibrant culture. It is the oldest and best-preserved Swahili settlement in East Africa and was declared a UNESCO World Heritage Site in 2001.': 'Lamu ni kisiwa kidogo kilicho karibu na pwani ya Kenya, kinachojulikana kwa historia yake tajiri, usanifu wa kuvutia na utamaduni changamfu. Ni makazi ya Waswahili ya zamani zaidi na yaliyohifadhiwa vizuri zaidi Afrika Mashariki, na kilitangazwa kuwa Eneo la Urithi wa Dunia la UNESCO mwaka 2001.',
        'Lamu life is relaxed and slow-paced, with locals and visitors moving on foot, donkeys, and boats instead of cars. This slow rhythm is part of the island’s charm and invites guests to savor every moment.': 'Maisha ya Lamu ni tulivu na ya polepole; wenyeji na wageni husafiri kwa miguu, punda na mashua badala ya magari. Mwendo huu wa polepole ni sehemu ya mvuto wa kisiwa na huwakaribisha wageni kufurahia kila wakati.',
        'Lamu has been inhabited for centuries and grew into one of the most important Swahili settlements on the East African coast. Its position along the Indian Ocean connected the island to merchants and travelers from Arabia, Persia, India, and the African mainland.': 'Lamu imekuwa na wakazi kwa karne nyingi na ikawa mojawapo ya makazi muhimu zaidi ya Waswahili katika pwani ya Afrika Mashariki. Eneo lake kando ya Bahari ya Hindi lilikihusisha kisiwa hicho na wafanyabiashara na wasafiri kutoka Arabia, Uajemi, India na bara la Afrika.',
        'By the 14th century, Lamu had become a lively trading port. Dhows carried spices, timber, ivory, textiles, and other goods between coastal towns and distant ports. This exchange shaped the island\'s language, architecture, food, faith, and traditions, creating the distinctive Swahili culture that visitors experience today.': 'Kufikia karne ya 14, Lamu ilikuwa bandari changamfu ya biashara. Majahazi yalisafirisha viungo, mbao, pembe za ndovu, vitambaa na bidhaa nyingine kati ya miji ya pwani na bandari za mbali. Biashara hii iliathiri lugha, usanifu, chakula, imani na mila za kisiwa, na kuunda utamaduni wa kipekee wa Kiswahili unaoonekana hadi leo.',
        'Lamu Old Town\'s coral-stone buildings, carved wooden doors, narrow streets, mosques, and courtyards preserve this maritime history. The town was recognized as a UNESCO World Heritage Site in 2001 because it is the oldest and best-preserved Swahili settlement in East Africa. Today, the island continues to protect its heritage while welcoming travelers to experience its living culture, beaches, and peaceful rhythm.': 'Majengo ya mawe ya matumbawe, milango ya mbao iliyochongwa, mitaa myembamba, misikiti na ua za Mji Mkongwe wa Lamu huhifadhi historia hii ya bahari. Mji huu ulitambuliwa kuwa Eneo la Urithi wa Dunia la UNESCO mwaka 2001 kwa kuwa ndio makazi ya Waswahili ya zamani zaidi na yaliyohifadhiwa vizuri zaidi Afrika Mashariki. Leo, kisiwa kinaendelea kulinda urithi wake huku kikiwakaribisha wasafiri kufurahia utamaduni hai, fukwe na maisha yake tulivu.',
        'The island is home to a unique blend of cultures, with influences from Arab, African, and Indian traditions. The local Swahili language and Islamic architecture are prominent features, and the experience here is a woven tapestry of Swahili culture, where community life, traditional crafts, and cuisine come together.': 'Kisiwa hiki kina mchanganyiko wa kipekee wa tamaduni zenye athari za mila za Kiarabu, Kiafrika na Kihindi. Lugha ya Kiswahili na usanifu wa Kiislamu ni sifa zake kuu; maisha ya jamii, ufundi wa jadi na vyakula huungana kuunda utamaduni wa Waswahili.',
        'Narrow streets, coral stone buildings, and historic mosques create an atmospheric walk through centuries of Swahili heritage. The architecture is a living museum of East African history.': 'Mitaa myembamba, majengo ya mawe ya matumbawe na misikiti ya kihistoria huleta matembezi yenye kuvutia katika urithi wa Waswahili wa karne nyingi. Usanifu huu ni makumbusho hai ya historia ya Afrika Mashariki.',
        'Pristine white sand beaches perfect for relaxation, swimming, and water sports. The clear turquoise waters of the Indian Ocean offer a tropical paradise experience.': 'Fukwe safi za mchanga mweupe zinafaa kwa mapumziko, kuogelea na michezo ya majini. Maji safi ya samawati ya Bahari ya Hindi yanatoa mandhari ya paradiso ya kitropiki.',
        'Learn about the island\'s rich history and culture through museums and traditional sites. Discover the stories of Swahili traders and the Islamic heritage of the island.': 'Jifunze kuhusu historia na utamaduni tajiri wa kisiwa kupitia makumbusho na maeneo ya jadi. Gundua simulizi za wafanyabiashara Waswahili na urithi wa Kiislamu wa kisiwa.',
        'Meet and interact with the famous Lamu donkeys that are central to island life. The sanctuary cares for these beloved animals that have served the community for generations.': 'Kutana na punda maarufu wa Lamu ambao ni sehemu muhimu ya maisha ya kisiwa. Hifadhi hii hutunza wanyama hawa wapendwa ambao wamehudumia jamii kwa vizazi.',
        'Experience life by walking, riding donkeys, and traveling by boat. This unique way of life has remained virtually unchanged for centuries, offering an authentic glimpse into Swahili culture.': 'Jionee maisha kwa kutembea, kupanda punda na kusafiri kwa mashua. Mtindo huu wa kipekee wa maisha umeendelea kwa karne nyingi na unatoa taswira halisi ya utamaduni wa Waswahili.',
        'Contact Us': 'Wasiliana Nasi',
        'Get in Touch': 'Wasiliana Nasi',
        'Address:': 'Anwani:',
        'Phone:': 'Simu:',
        'Email:': 'Barua pepe:',
        'Hours:': 'Saa za kazi:',
        'Monday - Friday: 9 AM - 6 PM': 'Jumatatu - Ijumaa: Saa 3 asubuhi - Saa 12 jioni',
        'Follow Us': 'Tufuate',
        'Send us a Message': 'Tutumie Ujumbe',
        'Name:': 'Jina:',
        'Email:': 'Barua pepe:',
        'Subject:': 'Mada:',
        'Message:': 'Ujumbe:',
        'Send Message': 'Tuma Ujumbe',
        'Book Your Tour or Stay': 'Hifadhi Ziara au Malazi Yako',
        'Full Name:': 'Jina Kamili:',
        'Email:': 'Barua pepe:',
        'Phone Number:': 'Nambari ya Simu:',
        'Country code': 'Msimbo wa nchi',
        'Select Tour or Stay:': 'Chagua Ziara au Malazi:',
        'Choose a tour or stay': 'Chagua ziara au malazi',
        'Preferred Date:': 'Tarehe Unayopendelea:',
        'Preferred Time:': 'Muda Unaopendelea:',
        'Number of Guests:': 'Idadi ya Wageni:',
        'Total Price: KSh 0': 'Jumla ya Bei: KSh 0',
        'Special Requests:': 'Maombi Maalum:',
        'Submit Booking Request': 'Tuma Ombi la Uhifadhi',
        'Sending request...': 'Ombi linatumwa...',
        'Welcome back': 'Karibu tena',
        'Log in to continue planning your Lamu experience.': 'Ingia ili uendelee kupanga matukio yako ya Lamu.',
        'Email address': 'Anwani ya barua pepe',
        'Password': 'Nenosiri',
        'Log in': 'Ingia',
        'New to Lamu Tours?': 'Mgeni katika Lamu Tours?',
        'Create an account': 'Fungua akaunti',
        'Create your account': 'Fungua akaunti yako',
        'Register to make and manage your Lamu tour bookings.': 'Jisajili ili kuweka na kudhibiti uhifadhi wako wa ziara za Lamu.',
        'Full name': 'Jina kamili',
        'Confirm password': 'Thibitisha nenosiri',
        'Create account': 'Fungua akaunti',
        'Already have an account?': 'Tayari una akaunti?',
        'Log in.': 'Ingia.',
        'List with us at a commission rate and get extra visibility.': 'Orodhesha makazi yako nasi kwa kamisheni na uyafanye yafahamike zaidi.',
        'List your property': 'Orodhesha Makazi Yako',
        'Are you an owner or property manager? Promote your hotel, home, guest house, or villa to travelers searching for a stay in Lamu.': 'Je, wewe ni mmiliki au msimamizi wa makazi? Tangaza hoteli, nyumba, nyumba ya wageni au vila yako kwa wasafiri wanaotafuta malazi Lamu.',
        'Your name': 'Jina lako',
        'Contact email': 'Barua pepe ya mawasiliano',
        'Property name': 'Jina la makazi',
        'Property type': 'Aina ya makazi',
        'Choose a type': 'Chagua aina',
        'Hotel': 'Hoteli',
        'Guest house': 'Nyumba ya wageni',
        'Villa': 'Vila',
        'Location': 'Mahali',
        'Price per night (USD)': 'Bei kwa usiku (USD)',
        'Guest capacity': 'Idadi ya wageni',
        'Image URL (optional)': 'Kiungo cha picha (si lazima)',
        'Describe your property': 'Eleza kuhusu makazi yako',
        'Submit property for listing': 'Wasilisha makazi yaorodheshwe',
        'Available Hospitality Partners': 'Washirika wa Malazi Wanaopatikana',
        'Comfortable, locally-owned guest houses with authentic Swahili hospitality.': 'Nyumba za wageni zinazomilikiwa na wenyeji, zenye starehe na ukarimu halisi wa Kiswahili.',
        'Stylish boutique hotels offering high-end comfort and personalized service.': 'Hoteli za kisasa zinazotoa starehe ya hali ya juu na huduma maalum.',
        'Private beach villas with ocean views, ideal for groups and luxury stays.': 'Vila za faragha ufukweni zenye mandhari ya bahari, bora kwa makundi na malazi ya kifahari.',
        'Local and international dining options with fresh seafood and Swahili dishes.': 'Chaguo za vyakula vya ndani na kimataifa, pamoja na vyakula vya baharini vibichi na vya Kiswahili.',
        'Cafes offering light meals, coffee, and snacks for travelers and locals.': 'Migahawa midogo inayotoa vyakula vyepesi, kahawa na vitafunio kwa wasafiri na wenyeji.',
        'Beach bars and lounge pubs with drinks, music, and relaxed atmosphere.': 'Baa za ufukweni na mapumziko zenye vinywaji, muziki na mazingira tulivu.',
        'Commission: 10%': 'Kamisheni: 10%',
        'Commission: 12%': 'Kamisheni: 12%',
        'Commission: 15%': 'Kamisheni: 15%',
        'Commission: 8%': 'Kamisheni: 8%',
        'Loading recently submitted properties...': 'Inapakia makazi yaliyowasilishwa hivi karibuni...',
        'Loading reviews...': 'Inapakia maoni...',
        'No reviews yet. Be the first to share your experience.': 'Bado hakuna maoni. Kuwa wa kwanza kushiriki uzoefu wako.',
        'Owner listings are temporarily unavailable.': 'Orodha za wamiliki hazipatikani kwa sasa.',
        'Reviews are temporarily unavailable.': 'Maoni hayapatikani kwa sasa.',
        'Guest Houses': 'Nyumba za Wageni',
        'Boutique Hotels': 'Hoteli za Kifahari',
        'Beach Villas': 'Vila za Ufukweni',
        'Restaurants': 'Mikahawa',
        'Cafes': 'Migahawa Midogo',
        'Bars': 'Baa',
        'Owner listings': 'Makazi Yaliyoorodheshwa na Wamiliki',
        'Share your Lamu experience': 'Shiriki Matukio Yako ya Lamu',
        'Tell future travelers about a place or stay you visited.': 'Waeleze wasafiri wa baadaye kuhusu mahali au malazi uliyotembelea.',
        'Your email': 'Barua pepe yako',
        'Place or stay': 'Mahali au malazi',
        'Choose a place': 'Chagua mahali',
        'Rating': 'Ukadiriaji',
        'Choose a rating': 'Chagua ukadiriaji',
        '5 - Excellent': '5 - Bora sana',
        '4 - Very good': '4 - Nzuri sana',
        '3 - Good': '3 - Nzuri',
        '2 - Fair': '2 - Wastani',
        '1 - Needs improvement': '1 - Inahitaji kuboreshwa',
        'Your review': 'Maoni yako',
        'Publish review': 'Chapisha Maoni',
        'Recent reviews': 'Maoni ya Hivi Karibuni',
        'Your booking request is confirmed': 'Ombi Lako la Uhifadhi Limethibitishwa',
        'Thank you for booking with Lamu Tours & Booking Agency. We have received your request and one of our travel advisors will contact you shortly to confirm the details.': 'Asante kwa kuweka nafasi kupitia Lamu Tours & Booking Agency. Tumepokea ombi lako na mshauri wetu wa safari atawasiliana nawe hivi karibuni kuthibitisha maelezo.',
        'What happens next:': 'Hatua zinazofuata:',
        'We will review your booking request.': 'Tutakagua ombi lako la uhifadhi.',
        'One of our team members will contact you by email or phone.': 'Mmoja wa timu yetu atawasiliana nawe kwa barua pepe au simu.',
        'Your tour details will be finalized and payment confirmed.': 'Maelezo ya ziara yako yatakamilishwa na malipo kuthibitishwa.',
        'Return to Home': 'Rudi Mwanzo',
        'Browse more tours': 'Tazama Ziara Zaidi',
        'Description:': 'Maelezo:',
        'Duration:': 'Muda:',
        'Price:': 'Bei:',
        'Includes:': 'Imejumuisha:',
        'Itinerary:': 'Ratiba:',
        'Book This Tour': 'Hifadhi Ziara Hii',
        'Tour Details': 'Maelezo ya Ziara',
        'Tour Not Found': 'Ziara Haikupatikana',
        'No tour matches the selected id. Please return to the tours list.': 'Hakuna ziara inayolingana na kitambulisho kilichochaguliwa. Tafadhali rudi kwenye orodha ya ziara.',
        'Please complete all fields.': 'Tafadhali jaza sehemu zote.',
        'Password must be at least 8 characters.': 'Nenosiri lazima liwe na angalau herufi 8.',
        'Passwords do not match.': 'Manenosiri hayalingani.',
        'An account with that email already exists.': 'Tayari kuna akaunti yenye anwani hiyo ya barua pepe.',
        'Invalid email or password.': 'Barua pepe au nenosiri si sahihi.',
        'United States/Canada': 'Marekani/ Kanada',
        'United States/Canada (+1)': 'Marekani/ Kanada (+1)',
        'United Kingdom': 'Uingereza',
        'United Kingdom (+44)': 'Uingereza (+44)',
        'South Africa': 'Afrika Kusini',
        'South Africa (+27)': 'Afrika Kusini (+27)',
        'United Arab Emirates': 'Falme za Kiarabu',
        'United Arab Emirates (+971)': 'Falme za Kiarabu (+971)',
        'Enter numbers only, without the country code': 'Ingiza nambari pekee, bila msimbo wa nchi',
        'e.g. Shela Palm House': 'mfano: Shela Palm House',
        'e.g. Shela, Lamu': 'mfano: Shela, Lamu',
        'e.g. 5000': 'mfano: 5000',
        'Tell travelers what makes your property special.': 'Waeleze wasafiri kinachofanya makazi yako yawe ya kipekee.',
        'What did you enjoy?': 'Umefurahia nini?',
        'All rights reserved.': 'Haki zote zimehifadhiwa.',
        '© 2026 Lamu Tours & Booking Agency. All rights reserved.': '© 2026 Lamu Tours & Booking Agency. Haki zote zimehifadhiwa.',
        'LamuTours.com is your trusted partner for online travel and related services.': 'LamuTours.com ni mshirika wako unayemwamini kwa usafiri wa mtandaoni na huduma zinazohusiana.'
    };

    const reverseTranslations = new Map(
        Object.entries(translations).map(([english, kiswahili]) => [kiswahili, english])
    );
    const originalText = new WeakMap();
    const appliedText = new WeakMap();
    const originalAttributes = new WeakMap();
    let currentLanguage = 'en';

    function englishText(value) {
        const text = value.trim();
        let replacement = reverseTranslations.get(text);
        const translatedCount = text.match(/^(\d+) (maeneo|mahali) yamepatikana$/);
        const translatedTotal = text.match(/^Jumla ya Bei: KSh ([\d,]+)$/);
        if (!replacement && translatedCount) {
            replacement = `${translatedCount[1]} ${translatedCount[2] === 'mahali' ? 'place' : 'places'} found`;
        } else if (!replacement && translatedTotal) {
            replacement = `Total Price: KSh ${translatedTotal[1]}`;
        }
        return replacement ? value.replace(text, replacement) : value;
    }

    function swahiliText(value) {
        const english = englishText(value);
        const text = english.trim();
        let replacement = translations[text];
        const count = text.match(/^(\d+) (places|place) found$/);
        const total = text.match(/^Total Price: KSh ([\d,]+)$/);
        if (!replacement && count) {
            replacement = `${count[1]} ${count[2] === 'place' ? 'mahali' : 'maeneo'} yamepatikana`;
        } else if (!replacement && total) {
            replacement = `Jumla ya Bei: KSh ${total[1]}`;
        }
        return replacement ? english.replace(text, replacement) : english;
    }

    function saveOriginalText(node) {
        if (!originalText.has(node)) originalText.set(node, node.nodeValue);
        return originalText.get(node);
    }

    function translateTextNode(node) {
        const original = saveOriginalText(node);
        if (node.parentElement?.closest('[data-price-kes]')) return;
        const isHomeOption = original.trim() === 'Home' &&
            node.parentNode instanceof Element &&
            node.parentNode.tagName === 'OPTION';
        const replacement = currentLanguage === 'sw'
            ? isHomeOption ? original.replace('Home', 'Nyumba') : swahiliText(original)
            : englishText(original);
        if (node.nodeValue !== replacement) {
            appliedText.set(node, replacement);
            node.nodeValue = replacement;
        } else {
            appliedText.set(node, replacement);
        }
    }

    function translateAttribute(element, attribute) {
        if (element.matches('[data-language-toggle]') && attribute === 'aria-label') return;
        const value = element.getAttribute(attribute);
        if (value === null) return;
        let originals = originalAttributes.get(element);
        if (!originals) {
            originals = new Map();
            originalAttributes.set(element, originals);
        }
        if (!originals.has(attribute)) originals.set(attribute, value);
        const original = originals.get(attribute);
        const replacement = currentLanguage === 'sw' ? swahiliText(original) : englishText(original);
        if (value !== replacement) element.setAttribute(attribute, replacement);
    }

    function translateTree(root) {
        if (root.nodeType === Node.TEXT_NODE) {
            translateTextNode(root);
            return;
        }
        if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
        const element = root.nodeType === Node.ELEMENT_NODE ? root : document.documentElement;
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        let textNode;
        while ((textNode = walker.nextNode())) translateTextNode(textNode);

        [element, ...element.querySelectorAll('*')].forEach((item) => {
            ['placeholder', 'title', 'aria-label', 'alt'].forEach((attribute) => {
                translateAttribute(item, attribute);
            });
        });
    }

    function setLanguage(language) {
        currentLanguage = language === 'sw' ? 'sw' : 'en';
        document.documentElement.lang = currentLanguage === 'sw' ? 'sw' : 'en';
        try {
            window.localStorage.setItem('lamu-tours-language', currentLanguage);
        } catch (error) {
            console.warn('Could not save the language preference.', error);
        }
        translateTree(document.documentElement);
        document.querySelectorAll('[data-language-toggle]').forEach((button) => {
            const target = currentLanguage === 'en' ? 'sw' : 'en';
            const targetName = target === 'sw' ? 'Kiswahili' : 'English';
            button.textContent = targetName;
            button.setAttribute(
                'aria-label',
                currentLanguage === 'en' ? 'Switch to Kiswahili' : translations['Switch to English']
            );
            button.setAttribute('aria-pressed', String(currentLanguage === 'sw'));
        });
        document.dispatchEvent(new CustomEvent('lamu-language-changed', {
            detail: { language: currentLanguage },
        }));
    }

    let preferredLanguage = 'en';
    try {
        preferredLanguage = window.localStorage.getItem('lamu-tours-language') || 'en';
    } catch (error) {
        console.warn('Could not read the saved language preference.', error);
    }

    document.querySelectorAll('[data-language-toggle]').forEach((button) => {
        button.addEventListener('click', () => {
            setLanguage(currentLanguage === 'en' ? 'sw' : 'en');
        });
    });

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'characterData') {
                const node = mutation.target;
                if (node.nodeValue !== appliedText.get(node)) {
                    const source = englishText(node.nodeValue);
                    originalText.set(node, source);
                    translateTextNode(node);
                }
            } else {
                mutation.addedNodes.forEach(translateTree);
                if (mutation.type === 'attributes') translateAttribute(mutation.target, mutation.attributeName);
            }
        });
    });

    observer.observe(document.documentElement, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['placeholder', 'title', 'aria-label', 'alt']
    });

    setLanguage(preferredLanguage);
})();
