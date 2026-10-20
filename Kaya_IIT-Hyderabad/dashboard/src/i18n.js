// Patient-app strings in English, Hindi, Telugu and Kannada.
// Hindi, Telugu and Kannada are first drafts and should be reviewed by a native speaker before clinical use.

export const LANGS = [
  { code: 'en', label: 'EN', locale: 'en-IN' },
  { code: 'hi', label: 'हिं', locale: 'hi-IN' },
  { code: 'te', label: 'తె', locale: 'te-IN' },
  { code: 'kn', label: 'ಕ', locale: 'kn-IN' },
]

const en = {
  tab_today: 'Today', tab_insights: 'Insights', tab_body: 'Body', tab_try: 'Try', ask_read_title: 'Should the AI read this report?', ask_saved: 'is saved.', ask_read_body: 'If you say yes, the file is sent to Sarvam AI, which reads the text. The results are added to your reports automatically and marked as not yet checked by a doctor. If you say no, nothing leaves this app.', ask_read_yes: 'Yes, read it for me', ask_read_no: 'No, keep the file only', sum_title: 'Added to your reports', sum_counts: '{n} results read · {k} outside the healthy range', sum_view: 'View the report', sum_note: 'Automatic reading can make mistakes. Check it against your paper copy and show it to your doctor.', up_readbtn: 'Read with AI', up_ocr: 'Read my report automatically', up_ocr_note: 'The file is sent to Sarvam AI to read the text. Untick to keep it private.', ocr_reading: 'Reading your report…', ocr_done: 'Added to your reports ({n} results)', ocr_text: 'Text added to your reports', ocr_failed: 'Could not read it. The file is saved.', ocr_notext: 'No text found. The file is saved.', up_title: 'Add a report', up_sub: 'Upload a PDF or a photo of a report from your hospital or lab. Your doctor can see it.', up_choose: 'Choose a PDF or photo', up_name: 'Name', up_type: 'Type', up_date: 'Date of the report', up_btn: 'Upload', up_busy: 'Uploading…', up_mine: 'Reports I uploaded', up_none: 'You have not uploaded any reports yet.', up_open: 'Open', up_remove: 'Remove', up_confirm: 'Remove this report?', up_note: 'Your doctor will look at your report themselves. Reading it automatically is optional.', up_big: 'That file is larger than 8 MB.', up_bad: 'Choose a PDF or a photo (PNG, JPEG or WebP).', cat_blood: 'Blood test', cat_scan: 'Scan or X-ray', cat_rx: 'Prescription', cat_discharge: 'Discharge summary', cat_eye: 'Eye report', cat_other: 'Other', now_title: 'WHAT TO DO NOW', also_today: 'Also today', all_done: 'All done for now. Well done!', a_meds_am: 'Take your morning medicines', a_meds_pm: 'Take your evening medicines', a_bed: 'Check your sugar before bed', a_walk: 'Take a 10-minute walk', r_low: 'Your sugar is {v} and may keep falling', r_high: 'Your sugar is forecast to reach about {v} in 2 hours', r_meds: 'Not marked as taken yet today', r_bed: 'Your medicines can cause a low during the night', r_walk: 'Only {n} steps so far today', log_title: 'Quick log', log_sub: 'Takes five seconds. Your doctor can see it.', log_meds: 'Medicines', morning: 'Morning', evening: 'Evening', log_walk: 'Walk', min: 'min', walked_today: '{n} min logged today', log_feel: 'How do I feel?', f_good: 'Good', f_ok: 'So-so', f_low: 'Unwell', tab_reports: 'Reports', rep_title1: 'My medical', rep_title2: 'reports', rep_trends: 'How my results are changing', rep_meds: 'My medicines', rep_all_title: 'All reports', rep_all: 'All', rep_back: 'Back to reports', rep_note: 'Reports are shown in English, as issued. The simple explanations are written for you, not by your doctor.', 
  today_title1: 'Your day', today_title2: 'for today', day_today: 'TODAY',
  st_low_title: 'Your sugar may dip soon', st_low_body: 'Have a small snack with some carbohydrate and check again in 15 minutes.', st_low_nudge: 'Have a small snack now',
  st_high_title: 'Your sugar may run high', st_high_body: 'A short walk after your meal helps your body use the sugar.', st_high_nudge: 'Take a 15-minute walk',
  st_ok_title: 'Your sugar is steady', st_ok_body: 'You are doing well. Keep your usual routine.', st_ok_nudge: 'Keep going: walk after dinner',
  mgdl_now: 'mg/dL now', one_thing: "TODAY'S ONE THING", mark_done: 'Mark as done', well_done: 'Well done!',
  my_habits: 'My habits', n_of_m: '{n} of {m} completed', completed: 'Completed', needs_attention: 'Needs attention',
  habit_range: 'Healthy range', habit_range_sub: '{pct} of the day, goal 70%',
  habit_steps: 'Steps', habit_steps_sub: '{n} of 6,000',
  habit_nolow: 'No low sugar', habit_nolow_sub_bad: '{pct} of the day below 70', habit_nolow_sub_ok: 'No dips below 70',
  habit_carbs: 'Carbs under 220 g', habit_carbs_sub: '{g} g in {m} meals',
  ins_title1: 'Time in range', ins_title2: 'weekly', today_lbl: 'Today', two_weeks: 'Two weeks',
  legend_in: 'In range {p}', legend_above: 'Above range {p}', legend_below: 'Below range {p}',
  ins_note: 'A good goal is more than 70% of the day in the healthy range.',
  body_title1: 'Your body', body_title2: 'what sugar does', liver: 'Liver', eyes: 'Eyes', kidneys: 'Kidneys',
  liver_high: 'Fat is likely building up', liver_mid: 'Some risk of fat build-up', liver_ok: 'Looking healthy',
  liver_text_mid: 'Habits matter here. Your doctor may suggest a scan.', liver_text_ok: 'Keep your habits steady.',
  eyes_text: 'Keep your yearly eye check.', kidney_watch: 'Your doctor is watching', kidney_ok: 'Tests look healthy',
  kidney_text: 'Kidney filter score {now} now, about {later} in five years at current habits.',
  body_note: 'The rings show your estimated chance over the next year (liver, eyes) and your latest kidney score. These are estimates to guide a conversation with your doctor.',
  dr0: 'No retinopathy', dr1: 'Mild', dr2: 'Moderate', dr3: 'Severe', dr4: 'Proliferative',
  try_title1: 'Try a change', try_title2: 'see what could happen',
  try_walk: 'Walk 20 min after meals', try_less: 'A quarter less rice and roti', try_both: 'Do both', with_change: 'With change',
  try_msg_tir: 'Your time in the healthy range could go from {a} to {b}', try_msg_gv: 'Your sugar swings could calm down by about {n}%',
  try_msg_liver: ', and your chance of liver fat build-up over a year from {a} to {b}.',
  try_note: 'This is a simulation to help you decide, not a promise. Talk to your doctor before changing your treatment.',
  ask_title: 'Ask Kaya', ask_hello: 'Hello! Ask me anything about your sugar, the screens, or how to use the app. You can type or tap the microphone.', ask_error: 'I could not answer just now. Please try again.', ask_nothing: 'I did not hear anything. Please try again.', ask_mic_error: 'Could not understand the recording. Please try again or type.', ask_no_mic: 'Microphone is not available on this device. Please type your question.', ask_mic_denied: 'Please allow the microphone to speak to Kaya.', ask_thinking: 'Thinking…', ask_stop: 'Stop recording', ask_speak: 'Speak', ask_listening: 'Listening… tap ■ when done', ask_placeholder: 'Type or speak your question', send: 'Send', close: 'Close', read_aloud: 'Read aloud', ask_note: 'General guidance from your data, not medical advice.', ask_s1: 'What does time in range mean?', ask_s2: 'Why is my sugar high?', ask_s3: 'Show my kidneys', ask_s4: 'How do I change the language?',   hello: 'Hello, {name}', day_good: 'A good day', day_ok: 'An average day', day_tough: 'A tough day', day_sub: 'Your sugar stayed in the healthy range for {pct} of the day.', day_spike: 'Biggest spike: {v} at {time}, about {m} min after a {g} g meal.', day_spike_nomeal: 'Highest sugar: {v} at {time}.', day_low: 'Low sugar for {m} minutes', day_nolow: 'No low sugar', day_chart: 'Your sugar through the day', what_happened: 'What happened',
  read_screen: 'Read this screen aloud', ask_fab: 'Ask', large_text: 'Large text',
  loading: 'Loading…', lang_note: 'Hindi, Telugu and Kannada are drafts pending native-speaker review.',
}

const hi = {
  tab_today: 'आज', tab_insights: 'जानकारी', tab_body: 'शरीर', tab_try: 'आज़माएँ', ask_read_title: 'क्या AI इस रिपोर्ट को पढ़े?', ask_saved: 'सहेज ली गई है।', ask_read_body: 'हाँ कहने पर फ़ाइल Sarvam AI को भेजी जाती है, जो टेक्स्ट पढ़ता है। नतीजे अपने आप आपकी रिपोर्ट में जुड़ जाते हैं और उन पर डॉक्टर ने अभी जाँचा नहीं लिखा रहता है। ना कहने पर कुछ भी इस ऐप से बाहर नहीं जाता।', ask_read_yes: 'हाँ, पढ़ दीजिए', ask_read_no: 'नहीं, सिर्फ़ फ़ाइल रखें', sum_title: 'आपकी रिपोर्ट में जोड़ा गया', sum_counts: '{n} नतीजे पढ़े गए · {k} सामान्य सीमा से बाहर', sum_view: 'रिपोर्ट देखें', sum_note: 'अपने आप पढ़ने में गलतियाँ हो सकती हैं। इसे अपनी कागज़ी कॉपी से मिलाएँ और डॉक्टर को दिखाएँ।', up_readbtn: 'AI से पढ़वाएँ', up_ocr: 'मेरी रिपोर्ट अपने आप पढ़ें', up_ocr_note: 'टेक्स्ट पढ़ने के लिए फ़ाइल Sarvam AI को भेजी जाती है। निजी रखने के लिए निशान हटाएँ।', ocr_reading: 'आपकी रिपोर्ट पढ़ी जा रही है…', ocr_done: 'आपकी रिपोर्ट में जोड़ा गया ({n} नतीजे)', ocr_text: 'टेक्स्ट आपकी रिपोर्ट में जोड़ा गया', ocr_failed: 'पढ़ नहीं सके। फ़ाइल सहेजी गई है।', ocr_notext: 'कोई टेक्स्ट नहीं मिला। फ़ाइल सहेजी गई है।', up_title: 'रिपोर्ट जोड़ें', up_sub: 'अस्पताल या लैब की रिपोर्ट का PDF या फ़ोटो अपलोड करें। आपके डॉक्टर इसे देख सकते हैं।', up_choose: 'PDF या फ़ोटो चुनें', up_name: 'नाम', up_type: 'प्रकार', up_date: 'रिपोर्ट की तारीख', up_btn: 'अपलोड करें', up_busy: 'अपलोड हो रहा है…', up_mine: 'मेरी अपलोड की गई रिपोर्ट', up_none: 'अभी कोई रिपोर्ट अपलोड नहीं की गई।', up_open: 'खोलें', up_remove: 'हटाएँ', up_confirm: 'यह रिपोर्ट हटाएँ?', up_note: 'आपके डॉक्टर आपकी रिपोर्ट खुद देखेंगे। अपने आप पढ़वाना वैकल्पिक है।', up_big: 'फ़ाइल 8 MB से बड़ी है।', up_bad: 'PDF या फ़ोटो (PNG, JPEG, WebP) चुनें।', cat_blood: 'खून की जाँच', cat_scan: 'स्कैन या एक्स-रे', cat_rx: 'पर्ची', cat_discharge: 'डिस्चार्ज सारांश', cat_eye: 'आँखों की रिपोर्ट', cat_other: 'अन्य', now_title: 'अभी क्या करें', also_today: 'आज और', all_done: 'अभी के लिए सब हो गया। शाबाश!', a_meds_am: 'सुबह की दवाइयाँ लें', a_meds_pm: 'शाम की दवाइयाँ लें', a_bed: 'सोने से पहले शुगर जाँचें', a_walk: '10 मिनट टहलें', r_low: 'आपकी शुगर {v} है और गिर सकती है', r_high: 'अगले 2 घंटे में शुगर लगभग {v} तक जा सकती है', r_meds: 'आज अभी तक लिया हुआ नहीं चुना गया', r_bed: 'आपकी दवाइयों से रात में शुगर कम हो सकती है', r_walk: 'आज अब तक सिर्फ़ {n} कदम', log_title: 'झटपट नोट', log_sub: 'पाँच सेकंड लगते हैं। आपके डॉक्टर इसे देख सकते हैं।', log_meds: 'दवाइयाँ', morning: 'सुबह', evening: 'शाम', log_walk: 'सैर', min: 'मिनट', walked_today: 'आज {n} मिनट दर्ज', log_feel: 'आप कैसा महसूस कर रहे हैं?', f_good: 'अच्छा', f_ok: 'ठीक-ठाक', f_low: 'तबीयत ठीक नहीं', tab_reports: 'रिपोर्ट', rep_title1: 'मेरी मेडिकल', rep_title2: 'रिपोर्ट', rep_trends: 'मेरे नतीजे कैसे बदल रहे हैं', rep_meds: 'मेरी दवाइयाँ', rep_all_title: 'सभी रिपोर्ट', rep_all: 'सभी', rep_back: 'रिपोर्ट पर वापस', rep_note: 'रिपोर्ट अंग्रेज़ी में जारी रूप में दिखती हैं। सरल व्याख्याएँ आपके लिए लिखी गई हैं, आपके डॉक्टर ने नहीं।', 
  today_title1: 'आपका दिन', today_title2: 'आज के लिए', day_today: 'आज',
  st_low_title: 'आपकी शुगर जल्द गिर सकती है', st_low_body: 'थोड़े कार्बोहाइड्रेट वाला हल्का नाश्ता लें और 15 मिनट बाद फिर जाँचें।', st_low_nudge: 'अभी हल्का नाश्ता करें',
  st_high_title: 'आपकी शुगर बढ़ सकती है', st_high_body: 'खाने के बाद थोड़ी सैर शरीर को शुगर इस्तेमाल करने में मदद करती है।', st_high_nudge: '15 मिनट टहलें',
  st_ok_title: 'आपकी शुगर स्थिर है', st_ok_body: 'आप अच्छा कर रहे हैं। अपनी सामान्य दिनचर्या जारी रखें।', st_ok_nudge: 'ऐसे ही चलते रहें: रात के खाने के बाद टहलें',
  mgdl_now: 'mg/dL अभी', one_thing: 'आज की एक बात', mark_done: 'पूरा हुआ', well_done: 'शाबाश!',
  my_habits: 'मेरी आदतें', n_of_m: '{m} में से {n} पूरी', completed: 'पूरी हुईं', needs_attention: 'ध्यान दें',
  habit_range: 'सामान्य सीमा', habit_range_sub: 'दिन का {pct}, लक्ष्य 70%',
  habit_steps: 'कदम', habit_steps_sub: '6,000 में से {n}',
  habit_nolow: 'शुगर कम नहीं हुई', habit_nolow_sub_bad: 'दिन का {pct} समय 70 से नीचे', habit_nolow_sub_ok: '70 से नीचे नहीं गई',
  habit_carbs: 'कार्ब्स 220 ग्राम से कम', habit_carbs_sub: '{m} भोजन में {g} ग्राम',
  ins_title1: 'सामान्य सीमा में समय', ins_title2: 'साप्ताहिक', today_lbl: 'आज', two_weeks: 'दो सप्ताह',
  legend_in: 'सीमा में {p}', legend_above: 'सीमा से ऊपर {p}', legend_below: 'सीमा से नीचे {p}',
  ins_note: 'अच्छा लक्ष्य है कि दिन का 70% से अधिक समय सामान्य सीमा में रहे।',
  body_title1: 'आपका शरीर', body_title2: 'शुगर का असर', liver: 'लिवर', eyes: 'आँखें', kidneys: 'किडनी',
  liver_high: 'चर्बी जमा होने की संभावना है', liver_mid: 'चर्बी जमा होने का कुछ जोखिम', liver_ok: 'ठीक दिख रहा है',
  liver_text_mid: 'यहाँ आदतें मायने रखती हैं। डॉक्टर स्कैन सुझा सकते हैं।', liver_text_ok: 'अपनी आदतें स्थिर रखें।',
  eyes_text: 'साल में एक बार आँखों की जाँच कराते रहें।', kidney_watch: 'आपके डॉक्टर नज़र रख रहे हैं', kidney_ok: 'जाँचें ठीक दिख रही हैं',
  kidney_text: 'किडनी फ़िल्टर स्कोर अभी {now}, मौजूदा आदतों पर पाँच साल में लगभग {later}।',
  body_note: 'रिंग अगले एक साल में आपकी अनुमानित संभावना (लिवर, आँखें) और आपका ताज़ा किडनी स्कोर दिखाती हैं। ये अनुमान डॉक्टर से बातचीत में मदद के लिए हैं।',
  dr0: 'रेटिनोपैथी नहीं', dr1: 'हल्की', dr2: 'मध्यम', dr3: 'गंभीर', dr4: 'प्रोलिफ़ेरेटिव',
  try_title1: 'बदलाव आज़माएँ', try_title2: 'देखें क्या हो सकता है',
  try_walk: 'खाने के बाद 20 मिनट टहलें', try_less: 'चावल और रोटी एक चौथाई कम करें', try_both: 'दोनों करें', with_change: 'बदलाव के साथ',
  try_msg_tir: 'सामान्य सीमा में आपका समय {a} से {b} तक हो सकता है', try_msg_gv: 'आपकी शुगर के उतार-चढ़ाव लगभग {n}% कम हो सकते हैं',
  try_msg_liver: ', और एक साल में लिवर में चर्बी जमा होने की संभावना {a} से {b} हो सकती है।',
  try_note: 'यह निर्णय में मदद के लिए एक सिमुलेशन है, वादा नहीं। इलाज बदलने से पहले अपने डॉक्टर से बात करें।',
  ask_title: 'केया से पूछें', ask_hello: 'नमस्ते! अपनी शुगर, स्क्रीन या ऐप इस्तेमाल करने के बारे में कुछ भी पूछिए। आप लिख सकते हैं या माइक्रोफ़ोन दबा सकते हैं।', ask_error: 'मैं अभी जवाब नहीं दे पाया। कृपया फिर कोशिश करें।', ask_nothing: 'कुछ सुनाई नहीं दिया। कृपया फिर कोशिश करें।', ask_mic_error: 'रिकॉर्डिंग समझ नहीं आई। कृपया फिर बोलें या लिखें।', ask_no_mic: 'इस डिवाइस पर माइक्रोफ़ोन उपलब्ध नहीं है। कृपया अपना सवाल लिखें।', ask_mic_denied: 'केया से बोलने के लिए कृपया माइक्रोफ़ोन की अनुमति दें।', ask_thinking: 'सोच रहा हूँ…', ask_stop: 'रिकॉर्डिंग रोकें', ask_speak: 'बोलें', ask_listening: 'सुन रहा हूँ… बोलकर ■ दबाएँ', ask_placeholder: 'अपना सवाल लिखें या बोलें', send: 'भेजें', close: 'बंद करें', read_aloud: 'ज़ोर से पढ़ें', ask_note: 'आपके डेटा पर आधारित सामान्य मार्गदर्शन, चिकित्सा सलाह नहीं।', ask_s1: 'सामान्य सीमा में समय का क्या मतलब है?', ask_s2: 'मेरी शुगर क्यों ज़्यादा है?', ask_s3: 'मेरी किडनी दिखाओ', ask_s4: 'भाषा कैसे बदलूँ?',   hello: 'नमस्ते, {name}', day_good: 'अच्छा दिन', day_ok: 'सामान्य दिन', day_tough: 'कठिन दिन', day_sub: 'दिन का {pct} समय आपकी शुगर सामान्य सीमा में रही।', day_spike: 'सबसे बड़ा उछाल: {time} पर {v}, लगभग {g} ग्राम भोजन के {m} मिनट बाद।', day_spike_nomeal: 'सबसे ज़्यादा शुगर: {time} पर {v}।', day_low: 'शुगर {m} मिनट तक कम रही', day_nolow: 'शुगर कम नहीं हुई', day_chart: 'दिनभर आपकी शुगर', what_happened: 'क्या हुआ',
  read_screen: 'यह स्क्रीन ज़ोर से पढ़ें', ask_fab: 'पूछें', large_text: 'बड़े अक्षर',
  loading: 'लोड हो रहा है…', lang_note: 'हिंदी, तेलुगु और कन्नड़ मूल वक्ता की समीक्षा तक प्रारूप हैं।',
}

const te = {
  tab_today: 'ఈరోజు', tab_insights: 'విశ్లేషణ', tab_body: 'శరీరం', tab_try: 'ప్రయత్నించండి', ask_read_title: 'ఈ రిపోర్ట్‌ను AI చదవాలా?', ask_saved: 'సేవ్ అయింది.', ask_read_body: 'అవును అంటే ఫైల్ Sarvam AIకి పంపబడుతుంది, అది టెక్స్ట్ చదువుతుంది. ఫలితాలు మీ రిపోర్టులకు ఆటోమేటిక్‌గా జోడించబడి, వైద్యుడు ఇంకా తనిఖీ చేయలేదు అని గుర్తించబడతాయి. కాదు అంటే ఏదీ ఈ యాప్ నుండి బయటకు వెళ్లదు.', ask_read_yes: 'అవును, చదవండి', ask_read_no: 'వద్దు, ఫైల్ మాత్రమే ఉంచండి', sum_title: 'మీ రిపోర్టులకు జోడించబడింది', sum_counts: '{n} ఫలితాలు చదివాం · {k} సాధారణ పరిధి బయట', sum_view: 'రిపోర్ట్ చూడండి', sum_note: 'ఆటోమేటిక్ రీడింగ్‌లో తప్పులు ఉండవచ్చు. మీ కాగితపు కాపీతో సరిచూసి వైద్యుడికి చూపించండి.', up_readbtn: 'AIతో చదివించండి', up_ocr: 'నా రిపోర్ట్‌ను ఆటోమేటిక్‌గా చదవండి', up_ocr_note: 'టెక్స్ట్ చదవడానికి ఫైల్ Sarvam AIకి పంపబడుతుంది. ప్రైవేట్‌గా ఉంచడానికి టిక్ తీసివేయండి.', ocr_reading: 'మీ రిపోర్ట్ చదువుతున్నాం…', ocr_done: 'మీ రిపోర్టులకు జోడించబడింది ({n} ఫలితాలు)', ocr_text: 'టెక్స్ట్ మీ రిపోర్టులకు జోడించబడింది', ocr_failed: 'చదవలేకపోయాం. ఫైల్ సేవ్ అయింది.', ocr_notext: 'టెక్స్ట్ కనిపించలేదు. ఫైల్ సేవ్ అయింది.', up_title: 'రిపోర్ట్ జోడించండి', up_sub: 'ఆసుపత్రి లేదా ల్యాబ్ రిపోర్ట్ యొక్క PDF లేదా ఫోటోను అప్‌లోడ్ చేయండి. మీ వైద్యుడు దీన్ని చూడగలరు.', up_choose: 'PDF లేదా ఫోటో ఎంచుకోండి', up_name: 'పేరు', up_type: 'రకం', up_date: 'రిపోర్ట్ తేదీ', up_btn: 'అప్‌లోడ్ చేయండి', up_busy: 'అప్‌లోడ్ అవుతోంది…', up_mine: 'నేను అప్‌లోడ్ చేసిన రిపోర్టులు', up_none: 'ఇంకా ఏ రిపోర్ట్ అప్‌లోడ్ చేయలేదు.', up_open: 'తెరవండి', up_remove: 'తొలగించండి', up_confirm: 'ఈ రిపోర్ట్‌ను తొలగించాలా?', up_note: 'మీ వైద్యుడు మీ రిపోర్ట్‌ను స్వయంగా చూస్తారు. ఆటోమేటిక్‌గా చదవడం ఐచ్ఛికం.', up_big: 'ఫైల్ 8 MB కంటే పెద్దది.', up_bad: 'PDF లేదా ఫోటో (PNG, JPEG, WebP) ఎంచుకోండి.', cat_blood: 'రక్త పరీక్ష', cat_scan: 'స్కాన్ లేదా ఎక్స్-రే', cat_rx: 'ప్రిస్క్రిప్షన్', cat_discharge: 'డిశ్చార్జ్ సారాంశం', cat_eye: 'కంటి రిపోర్ట్', cat_other: 'ఇతరం', now_title: 'ఇప్పుడు ఏం చేయాలి', also_today: 'ఈరోజు ఇంకా', all_done: 'ప్రస్తుతానికి అన్నీ అయ్యాయి. చాలా బాగుంది!', a_meds_am: 'ఉదయం మందులు వేసుకోండి', a_meds_pm: 'సాయంత్రం మందులు వేసుకోండి', a_bed: 'పడుకునే ముందు షుగర్ చూడండి', a_walk: '10 నిమిషాలు నడవండి', r_low: 'మీ షుగర్ {v} ఉంది, ఇంకా తగ్గవచ్చు', r_high: 'రాబోయే 2 గంటల్లో షుగర్ సుమారు {v} వరకు పెరగవచ్చు', r_meds: 'ఈరోజు ఇంకా వేసుకున్నట్లు గుర్తించలేదు', r_bed: 'మీ మందుల వల్ల రాత్రిపూట షుగర్ తగ్గవచ్చు', r_walk: 'ఈరోజు ఇప్పటివరకు {n} అడుగులే', log_title: 'త్వరిత నమోదు', log_sub: 'ఐదు సెకన్లు చాలు. మీ వైద్యుడు దీన్ని చూడగలరు.', log_meds: 'మందులు', morning: 'ఉదయం', evening: 'సాయంత్రం', log_walk: 'నడక', min: 'నిమి', walked_today: 'ఈరోజు {n} నిమిషాలు నమోదు', log_feel: 'మీకు ఎలా అనిపిస్తోంది?', f_good: 'బాగుంది', f_ok: 'పర్వాలేదు', f_low: 'బాగాలేదు', tab_reports: 'నివేదికలు', rep_title1: 'నా వైద్య', rep_title2: 'నివేదికలు', rep_trends: 'నా ఫలితాలు ఎలా మారుతున్నాయి', rep_meds: 'నా మందులు', rep_all_title: 'అన్ని నివేదికలు', rep_all: 'అన్నీ', rep_back: 'నివేదికలకు తిరిగి', rep_note: 'నివేదికలు ఇచ్చినట్లే ఆంగ్లంలో కనిపిస్తాయి. సులభ వివరణలు మీ కోసం రాసినవి, మీ వైద్యుడు రాసినవి కావు.', 
  today_title1: 'మీ రోజు', today_title2: 'ఈరోజు కోసం', day_today: 'ఈరోజు',
  st_low_title: 'మీ షుగర్ త్వరలో తగ్గవచ్చు', st_low_body: 'కొంచెం కార్బోహైడ్రేట్ ఉన్న చిన్న అల్పాహారం తీసుకోండి, 15 నిమిషాల తర్వాత మళ్లీ చూడండి.', st_low_nudge: 'ఇప్పుడు చిన్న అల్పాహారం తీసుకోండి',
  st_high_title: 'మీ షుగర్ పెరగవచ్చు', st_high_body: 'భోజనం తర్వాత కొంచెం నడిస్తే శరీరం షుగర్‌ను వాడుకోవడానికి సహాయపడుతుంది.', st_high_nudge: '15 నిమిషాలు నడవండి',
  st_ok_title: 'మీ షుగర్ స్థిరంగా ఉంది', st_ok_body: 'మీరు బాగా చేస్తున్నారు. మీ రోజువారీ అలవాట్లను కొనసాగించండి.', st_ok_nudge: 'ఇలాగే కొనసాగండి: రాత్రి భోజనం తర్వాత నడవండి',
  mgdl_now: 'mg/dL ఇప్పుడు', one_thing: 'ఈరోజు ఒక్క పని', mark_done: 'పూర్తయింది', well_done: 'చాలా బాగుంది!',
  my_habits: 'నా అలవాట్లు', n_of_m: '{m}లో {n} పూర్తి', completed: 'పూర్తయినవి', needs_attention: 'శ్రద్ధ అవసరం',
  habit_range: 'సాధారణ పరిధి', habit_range_sub: 'రోజులో {pct}, లక్ష్యం 70%',
  habit_steps: 'అడుగులు', habit_steps_sub: '6,000లో {n}',
  habit_nolow: 'షుగర్ తగ్గలేదు', habit_nolow_sub_bad: 'రోజులో {pct} సమయం 70 కంటే తక్కువ', habit_nolow_sub_ok: '70 కంటే తగ్గలేదు',
  habit_carbs: 'కార్బ్స్ 220 గ్రాముల లోపు', habit_carbs_sub: '{m} భోజనాల్లో {g} గ్రాములు',
  ins_title1: 'పరిధిలో సమయం', ins_title2: 'వారం వారీ', today_lbl: 'ఈరోజు', two_weeks: 'రెండు వారాలు',
  legend_in: 'పరిధిలో {p}', legend_above: 'పరిధి పైన {p}', legend_below: 'పరిధి కింద {p}',
  ins_note: 'రోజులో 70% కంటే ఎక్కువ సమయం సాధారణ పరిధిలో ఉండటం మంచి లక్ష్యం.',
  body_title1: 'మీ శరీరం', body_title2: 'షుగర్ ప్రభావం', liver: 'కాలేయం', eyes: 'కళ్ళు', kidneys: 'మూత్రపిండాలు',
  liver_high: 'కొవ్వు పేరుకుపోయే అవకాశం ఎక్కువ', liver_mid: 'కొంత కొవ్వు పేరుకునే ప్రమాదం', liver_ok: 'ఆరోగ్యంగా ఉంది',
  liver_text_mid: 'ఇక్కడ అలవాట్లు ముఖ్యం. డాక్టర్ స్కాన్ సూచించవచ్చు.', liver_text_ok: 'మీ అలవాట్లను స్థిరంగా ఉంచండి.',
  eyes_text: 'ప్రతి సంవత్సరం కంటి పరీక్ష చేయించుకోండి.', kidney_watch: 'మీ డాక్టర్ గమనిస్తున్నారు', kidney_ok: 'పరీక్షలు బాగున్నాయి',
  kidney_text: 'కిడ్నీ ఫిల్టర్ స్కోర్ ఇప్పుడు {now}, ప్రస్తుత అలవాట్లతో ఐదు సంవత్సరాల్లో సుమారు {later}.',
  body_note: 'రింగులు రాబోయే ఏడాదిలో మీ అంచనా అవకాశాన్ని (కాలేయం, కళ్ళు), తాజా కిడ్నీ స్కోర్‌ను చూపిస్తాయి. ఇవి డాక్టర్‌తో చర్చకు సహాయపడే అంచనాలు.',
  dr0: 'రెటినోపతి లేదు', dr1: 'స్వల్పం', dr2: 'మధ్యస్థం', dr3: 'తీవ్రం', dr4: 'ప్రొలిఫరేటివ్',
  try_title1: 'మార్పు ప్రయత్నించండి', try_title2: 'ఏమవుతుందో చూడండి',
  try_walk: 'భోజనం తర్వాత 20 నిమిషాలు నడవండి', try_less: 'అన్నం, రొట్టె పావు వంతు తగ్గించండి', try_both: 'రెండూ చేయండి', with_change: 'మార్పుతో',
  try_msg_tir: 'సాధారణ పరిధిలో మీ సమయం {a} నుండి {b}కి పెరగవచ్చు', try_msg_gv: 'మీ షుగర్ హెచ్చుతగ్గులు సుమారు {n}% తగ్గవచ్చు',
  try_msg_liver: ', ఒక సంవత్సరంలో కాలేయంలో కొవ్వు పేరుకునే అవకాశం {a} నుండి {b}కి తగ్గవచ్చు.',
  try_note: 'ఇది నిర్ణయానికి సహాయపడే సిమ్యులేషన్ మాత్రమే, హామీ కాదు. చికిత్సలో మార్పు చేసే ముందు మీ డాక్టర్‌తో మాట్లాడండి.',
  ask_title: 'కేయాను అడగండి', ask_hello: 'నమస్కారం! మీ షుగర్ గురించి, స్క్రీన్\u200cల గురించి లేదా యాప్ ఎలా వాడాలో ఏదైనా అడగండి. మీరు టైప్ చేయవచ్చు లేదా మైక్రోఫోన్ నొక్కవచ్చు.', ask_error: 'నేను ఇప్పుడు సమాధానం ఇవ్వలేకపోయాను. దయచేసి మళ్లీ ప్రయత్నించండి.', ask_nothing: 'ఏమీ వినిపించలేదు. దయచేసి మళ్లీ ప్రయత్నించండి.', ask_mic_error: 'రికార్డింగ్ అర్థం కాలేదు. దయచేసి మళ్లీ మాట్లాడండి లేదా టైప్ చేయండి.', ask_no_mic: 'ఈ పరికరంలో మైక్రోఫోన్ అందుబాటులో లేదు. దయచేసి మీ ప్రశ్నను టైప్ చేయండి.', ask_mic_denied: 'కేయాతో మాట్లాడడానికి దయచేసి మైక్రోఫోన్ అనుమతి ఇవ్వండి.', ask_thinking: 'ఆలోచిస్తున్నాను…', ask_stop: 'రికార్డింగ్ ఆపండి', ask_speak: 'మాట్లాడండి', ask_listening: 'వింటున్నాను… పూర్తయ్యాక ■ నొక్కండి', ask_placeholder: 'మీ ప్రశ్న టైప్ చేయండి లేదా చెప్పండి', send: 'పంపండి', close: 'మూసివేయండి', read_aloud: 'గట్టిగా చదవండి', ask_note: 'మీ డేటా ఆధారిత సాధారణ మార్గదర్శకం, వైద్య సలహా కాదు.', ask_s1: 'పరిధిలో సమయం అంటే ఏమిటి?', ask_s2: 'నా షుగర్ ఎందుకు ఎక్కువగా ఉంది?', ask_s3: 'నా కిడ్నీలు చూపించండి', ask_s4: 'భాష ఎలా మార్చాలి?',   hello: 'నమస్కారం, {name}', day_good: 'మంచి రోజు', day_ok: 'సాధారణ రోజు', day_tough: 'కష్టమైన రోజు', day_sub: 'రోజులో {pct} సమయం మీ షుగర్ సాధారణ పరిధిలో ఉంది.', day_spike: 'అత్యధిక పెరుగుదల: {time}కి {v}, సుమారు {g} గ్రాముల భోజనం తర్వాత {m} నిమిషాలకు.', day_spike_nomeal: 'అత్యధిక షుగర్: {time}కి {v}.', day_low: 'షుగర్ {m} నిమిషాలు తక్కువగా ఉంది', day_nolow: 'షుగర్ తగ్గలేదు', day_chart: 'రోజంతా మీ షుగర్', what_happened: 'ఏం జరిగింది',
  read_screen: 'ఈ స్క్రీన్ గట్టిగా చదవండి', ask_fab: 'అడగండి', large_text: 'పెద్ద అక్షరాలు',
  loading: 'లోడ్ అవుతోంది…', lang_note: 'హిందీ, తెలుగు, కన్నడ అనువాదాలు స్థానిక భాషా నిపుణుల సమీక్ష వరకు ముసాయిదాలు.',
}

const kn = {
  tab_today: 'ಇಂದು', tab_insights: 'ವಿಶ್ಲೇಷಣೆ', tab_body: 'ದೇಹ', tab_try: 'ಪ್ರಯತ್ನಿಸಿ', ask_read_title: 'ಈ ವರದಿಯನ್ನು AI ಓದಬೇಕೇ?', ask_saved: 'ಉಳಿಸಲಾಗಿದೆ.', ask_read_body: 'ಹೌದು ಎಂದರೆ ಫೈಲ್ ಅನ್ನು Sarvam AI ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ, ಅದು ಪಠ್ಯವನ್ನು ಓದುತ್ತದೆ. ಫಲಿತಾಂಶಗಳು ನಿಮ್ಮ ವರದಿಗಳಿಗೆ ತಾನಾಗಿ ಸೇರುತ್ತವೆ ಮತ್ತು ವೈದ್ಯರು ಇನ್ನೂ ಪರಿಶೀಲಿಸಿಲ್ಲ ಎಂದು ಗುರುತಿಸಲಾಗುತ್ತದೆ. ಇಲ್ಲ ಎಂದರೆ ಏನೂ ಈ ಆ್ಯಪ್‌ನಿಂದ ಹೊರಗೆ ಹೋಗುವುದಿಲ್ಲ.', ask_read_yes: 'ಹೌದು, ಓದಿ', ask_read_no: 'ಬೇಡ, ಫೈಲ್ ಮಾತ್ರ ಇರಿಸಿ', sum_title: 'ನಿಮ್ಮ ವರದಿಗಳಿಗೆ ಸೇರಿಸಲಾಗಿದೆ', sum_counts: '{n} ಫಲಿತಾಂಶಗಳನ್ನು ಓದಲಾಗಿದೆ · {k} ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿಯ ಹೊರಗೆ', sum_view: 'ವರದಿ ನೋಡಿ', sum_note: 'ತಾನಾಗಿ ಓದುವಾಗ ತಪ್ಪುಗಳಾಗಬಹುದು. ನಿಮ್ಮ ಕಾಗದದ ಪ್ರತಿಯೊಂದಿಗೆ ಹೋಲಿಸಿ ವೈದ್ಯರಿಗೆ ತೋರಿಸಿ.', up_readbtn: 'AI ಯಿಂದ ಓದಿಸಿ', up_ocr: 'ನನ್ನ ವರದಿಯನ್ನು ತಾನಾಗಿ ಓದಿ', up_ocr_note: 'ಪಠ್ಯ ಓದಲು ಫೈಲ್ ಅನ್ನು Sarvam AI ಗೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ. ಖಾಸಗಿಯಾಗಿರಿಸಲು ಟಿಕ್ ತೆಗೆಯಿರಿ.', ocr_reading: 'ನಿಮ್ಮ ವರದಿಯನ್ನು ಓದುತ್ತಿದ್ದೇವೆ…', ocr_done: 'ನಿಮ್ಮ ವರದಿಗಳಿಗೆ ಸೇರಿಸಲಾಗಿದೆ ({n} ಫಲಿತಾಂಶಗಳು)', ocr_text: 'ಪಠ್ಯವನ್ನು ನಿಮ್ಮ ವರದಿಗಳಿಗೆ ಸೇರಿಸಲಾಗಿದೆ', ocr_failed: 'ಓದಲು ಆಗಲಿಲ್ಲ. ಫೈಲ್ ಉಳಿಸಲಾಗಿದೆ.', ocr_notext: 'ಪಠ್ಯ ಸಿಗಲಿಲ್ಲ. ಫೈಲ್ ಉಳಿಸಲಾಗಿದೆ.', up_title: 'ವರದಿ ಸೇರಿಸಿ', up_sub: 'ಆಸ್ಪತ್ರೆ ಅಥವಾ ಲ್ಯಾಬ್ ವರದಿಯ PDF ಅಥವಾ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ. ನಿಮ್ಮ ವೈದ್ಯರು ಇದನ್ನು ನೋಡಬಹುದು.', up_choose: 'PDF ಅಥವಾ ಫೋಟೋ ಆಯ್ಕೆಮಾಡಿ', up_name: 'ಹೆಸರು', up_type: 'ವಿಧ', up_date: 'ವರದಿಯ ದಿನಾಂಕ', up_btn: 'ಅಪ್‌ಲೋಡ್ ಮಾಡಿ', up_busy: 'ಅಪ್‌ಲೋಡ್ ಆಗುತ್ತಿದೆ…', up_mine: 'ನಾನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ವರದಿಗಳು', up_none: 'ಇನ್ನೂ ಯಾವುದೇ ವರದಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿಲ್ಲ.', up_open: 'ತೆರೆಯಿರಿ', up_remove: 'ತೆಗೆಯಿರಿ', up_confirm: 'ಈ ವರದಿಯನ್ನು ತೆಗೆಯಬೇಕೇ?', up_note: 'ನಿಮ್ಮ ವೈದ್ಯರು ನಿಮ್ಮ ವರದಿಯನ್ನು ಸ್ವತಃ ನೋಡುತ್ತಾರೆ. ತಾನಾಗಿ ಓದುವುದು ಐಚ್ಛಿಕ.', up_big: 'ಫೈಲ್ 8 MB ಗಿಂತ ದೊಡ್ಡದಾಗಿದೆ.', up_bad: 'PDF ಅಥವಾ ಫೋಟೋ (PNG, JPEG, WebP) ಆಯ್ಕೆಮಾಡಿ.', cat_blood: 'ರಕ್ತ ಪರೀಕ್ಷೆ', cat_scan: 'ಸ್ಕ್ಯಾನ್ ಅಥವಾ ಎಕ್ಸ್-ರೇ', cat_rx: 'ಚೀಟಿ', cat_discharge: 'ಡಿಸ್ಚಾರ್ಜ್ ಸಾರಾಂಶ', cat_eye: 'ಕಣ್ಣಿನ ವರದಿ', cat_other: 'ಇತರೆ', now_title: 'ಈಗ ಏನು ಮಾಡಬೇಕು', also_today: 'ಇಂದು ಇನ್ನೂ', all_done: 'ಸದ್ಯಕ್ಕೆ ಎಲ್ಲವೂ ಆಯಿತು. ಅದ್ಭುತ!', a_meds_am: 'ಬೆಳಗಿನ ಔಷಧಿ ತೆಗೆದುಕೊಳ್ಳಿ', a_meds_pm: 'ಸಂಜೆಯ ಔಷಧಿ ತೆಗೆದುಕೊಳ್ಳಿ', a_bed: 'ಮಲಗುವ ಮೊದಲು ಶುಗರ್ ಪರೀಕ್ಷಿಸಿ', a_walk: '10 ನಿಮಿಷ ನಡೆಯಿರಿ', r_low: 'ನಿಮ್ಮ ಶುಗರ್ {v} ಇದೆ, ಇನ್ನೂ ಇಳಿಯಬಹುದು', r_high: 'ಮುಂದಿನ 2 ಗಂಟೆಗಳಲ್ಲಿ ಶುಗರ್ ಸುಮಾರು {v} ತಲುಪಬಹುದು', r_meds: 'ಇಂದು ಇನ್ನೂ ತೆಗೆದುಕೊಂಡಿರುವುದಾಗಿ ಗುರುತಿಸಿಲ್ಲ', r_bed: 'ನಿಮ್ಮ ಔಷಧಿಗಳಿಂದ ರಾತ್ರಿ ಶುಗರ್ ಕಡಿಮೆಯಾಗಬಹುದು', r_walk: 'ಇಂದು ಇಲ್ಲಿಯವರೆಗೆ {n} ಹೆಜ್ಜೆ ಮಾತ್ರ', log_title: 'ತ್ವರಿತ ದಾಖಲೆ', log_sub: 'ಐದು ಸೆಕೆಂಡ್ ಸಾಕು. ನಿಮ್ಮ ವೈದ್ಯರು ಇದನ್ನು ನೋಡಬಹುದು.', log_meds: 'ಔಷಧಿಗಳು', morning: 'ಬೆಳಗ್ಗೆ', evening: 'ಸಂಜೆ', log_walk: 'ನಡಿಗೆ', min: 'ನಿಮಿ', walked_today: 'ಇಂದು {n} ನಿಮಿಷ ದಾಖಲು', log_feel: 'ನಿಮಗೆ ಹೇಗೆ ಅನಿಸುತ್ತಿದೆ?', f_good: 'ಚೆನ್ನಾಗಿದೆ', f_ok: 'ಪರವಾಗಿಲ್ಲ', f_low: 'ಆರೋಗ್ಯ ಸರಿಯಿಲ್ಲ', tab_reports: 'ವರದಿಗಳು', rep_title1: 'ನನ್ನ ವೈದ್ಯಕೀಯ', rep_title2: 'ವರದಿಗಳು', rep_trends: 'ನನ್ನ ಫಲಿತಾಂಶಗಳು ಹೇಗೆ ಬದಲಾಗುತ್ತಿವೆ', rep_meds: 'ನನ್ನ ಔಷಧಿಗಳು', rep_all_title: 'ಎಲ್ಲಾ ವರದಿಗಳು', rep_all: 'ಎಲ್ಲಾ', rep_back: 'ವರದಿಗಳಿಗೆ ಹಿಂದೆ', rep_note: 'ವರದಿಗಳು ನೀಡಿದಂತೆ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ತೋರಿಸಲಾಗುತ್ತದೆ. ಸರಳ ವಿವರಣೆಗಳು ನಿಮಗಾಗಿ ಬರೆದವು, ನಿಮ್ಮ ವೈದ್ಯರದ್ದಲ್ಲ.', 
  today_title1: 'ನಿಮ್ಮ ದಿನ', today_title2: 'ಇಂದಿಗಾಗಿ', day_today: 'ಇಂದು',
  st_low_title: 'ನಿಮ್ಮ ಶುಗರ್ ಶೀಘ್ರದಲ್ಲೇ ಇಳಿಯಬಹುದು', st_low_body: 'ಸ್ವಲ್ಪ ಕಾರ್ಬೋಹೈಡ್ರೇಟ್ ಇರುವ ಲಘು ತಿಂಡಿ ತೆಗೆದುಕೊಳ್ಳಿ, 15 ನಿಮಿಷಗಳ ನಂತರ ಮತ್ತೆ ಪರಿಶೀಲಿಸಿ.', st_low_nudge: 'ಈಗ ಲಘು ತಿಂಡಿ ತೆಗೆದುಕೊಳ್ಳಿ',
  st_high_title: 'ನಿಮ್ಮ ಶುಗರ್ ಹೆಚ್ಚಾಗಬಹುದು', st_high_body: 'ಊಟದ ನಂತರ ಸ್ವಲ್ಪ ನಡೆದರೆ ದೇಹವು ಶುಗರ್ ಬಳಸಲು ಸಹಾಯವಾಗುತ್ತದೆ.', st_high_nudge: '15 ನಿಮಿಷ ನಡೆಯಿರಿ',
  st_ok_title: 'ನಿಮ್ಮ ಶುಗರ್ ಸ್ಥಿರವಾಗಿದೆ', st_ok_body: 'ನೀವು ಚೆನ್ನಾಗಿ ಮಾಡುತ್ತಿದ್ದೀರಿ. ನಿಮ್ಮ ಸಾಮಾನ್ಯ ದಿನಚರಿಯನ್ನು ಮುಂದುವರಿಸಿ.', st_ok_nudge: 'ಹೀಗೆಯೇ ಮುಂದುವರಿಸಿ: ರಾತ್ರಿ ಊಟದ ನಂತರ ನಡೆಯಿರಿ',
  mgdl_now: 'mg/dL ಈಗ', one_thing: 'ಇಂದಿನ ಒಂದು ಕೆಲಸ', mark_done: 'ಮುಗಿಯಿತು', well_done: 'ಅದ್ಭುತ!',
  my_habits: 'ನನ್ನ ಅಭ್ಯಾಸಗಳು', n_of_m: '{m}ರಲ್ಲಿ {n} ಪೂರ್ಣ', completed: 'ಪೂರ್ಣಗೊಂಡವು', needs_attention: 'ಗಮನ ಬೇಕು',
  habit_range: 'ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿ', habit_range_sub: 'ದಿನದ {pct}, ಗುರಿ 70%',
  habit_steps: 'ಹೆಜ್ಜೆಗಳು', habit_steps_sub: '6,000ರಲ್ಲಿ {n}',
  habit_nolow: 'ಶುಗರ್ ಇಳಿಯಲಿಲ್ಲ', habit_nolow_sub_bad: 'ದಿನದ {pct} ಸಮಯ 70ಕ್ಕಿಂತ ಕಡಿಮೆ', habit_nolow_sub_ok: '70ಕ್ಕಿಂತ ಕಡಿಮೆಯಾಗಿಲ್ಲ',
  habit_carbs: 'ಕಾರ್ಬ್ಸ್ 220 ಗ್ರಾಂ ಒಳಗೆ', habit_carbs_sub: '{m} ಊಟಗಳಲ್ಲಿ {g} ಗ್ರಾಂ',
  ins_title1: 'ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ಸಮಯ', ins_title2: 'ವಾರದ', today_lbl: 'ಇಂದು', two_weeks: 'ಎರಡು ವಾರ',
  legend_in: 'ವ್ಯಾಪ್ತಿಯಲ್ಲಿ {p}', legend_above: 'ವ್ಯಾಪ್ತಿಗಿಂತ ಮೇಲೆ {p}', legend_below: 'ವ್ಯಾಪ್ತಿಗಿಂತ ಕೆಳಗೆ {p}',
  ins_note: 'ದಿನದ 70%ಕ್ಕಿಂತ ಹೆಚ್ಚು ಸಮಯ ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿಯಲ್ಲಿರುವುದು ಒಳ್ಳೆಯ ಗುರಿ.',
  body_title1: 'ನಿಮ್ಮ ದೇಹ', body_title2: 'ಶುಗರ್‌ನ ಪರಿಣಾಮ', liver: 'ಯಕೃತ್ತು', eyes: 'ಕಣ್ಣುಗಳು', kidneys: 'ಮೂತ್ರಪಿಂಡಗಳು',
  liver_high: 'ಕೊಬ್ಬು ಶೇಖರಣೆಯಾಗುತ್ತಿರುವ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು', liver_mid: 'ಸ್ವಲ್ಪ ಕೊಬ್ಬು ಶೇಖರಣೆಯ ಅಪಾಯ', liver_ok: 'ಆರೋಗ್ಯವಾಗಿದೆ',
  liver_text_mid: 'ಇಲ್ಲಿ ಅಭ್ಯಾಸಗಳು ಮುಖ್ಯ. ವೈದ್ಯರು ಸ್ಕ್ಯಾನ್ ಸೂಚಿಸಬಹುದು.', liver_text_ok: 'ನಿಮ್ಮ ಅಭ್ಯಾಸಗಳನ್ನು ಸ್ಥಿರವಾಗಿಡಿ.',
  eyes_text: 'ವರ್ಷಕ್ಕೊಮ್ಮೆ ಕಣ್ಣಿನ ತಪಾಸಣೆ ಮಾಡಿಸಿಕೊಳ್ಳಿ.', kidney_watch: 'ನಿಮ್ಮ ವೈದ್ಯರು ಗಮನಿಸುತ್ತಿದ್ದಾರೆ', kidney_ok: 'ಪರೀಕ್ಷೆಗಳು ಚೆನ್ನಾಗಿವೆ',
  kidney_text: 'ಕಿಡ್ನಿ ಫಿಲ್ಟರ್ ಸ್ಕೋರ್ ಈಗ {now}, ಈಗಿನ ಅಭ್ಯಾಸಗಳೊಂದಿಗೆ ಐದು ವರ್ಷಗಳಲ್ಲಿ ಸುಮಾರು {later}.',
  body_note: 'ರಿಂಗ್‌ಗಳು ಮುಂದಿನ ಒಂದು ವರ್ಷದ ನಿಮ್ಮ ಅಂದಾಜು ಸಾಧ್ಯತೆಯನ್ನು (ಯಕೃತ್ತು, ಕಣ್ಣುಗಳು) ಮತ್ತು ಇತ್ತೀಚಿನ ಕಿಡ್ನಿ ಸ್ಕೋರ್ ಅನ್ನು ತೋರಿಸುತ್ತವೆ. ಇವು ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚೆಗೆ ಸಹಾಯ ಮಾಡುವ ಅಂದಾಜುಗಳು.',
  dr0: 'ರೆಟಿನೋಪತಿ ಇಲ್ಲ', dr1: 'ಸೌಮ್ಯ', dr2: 'ಮಧ್ಯಮ', dr3: 'ತೀವ್ರ', dr4: 'ಪ್ರೊಲಿಫರೇಟಿವ್',
  try_title1: 'ಬದಲಾವಣೆ ಪ್ರಯತ್ನಿಸಿ', try_title2: 'ಏನಾಗಬಹುದು ನೋಡಿ',
  try_walk: 'ಊಟದ ನಂತರ 20 ನಿಮಿಷ ನಡೆಯಿರಿ', try_less: 'ಅನ್ನ, ರೊಟ್ಟಿ ಕಾಲು ಭಾಗ ಕಡಿಮೆ ಮಾಡಿ', try_both: 'ಎರಡನ್ನೂ ಮಾಡಿ', with_change: 'ಬದಲಾವಣೆಯೊಂದಿಗೆ',
  try_msg_tir: 'ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ನಿಮ್ಮ ಸಮಯ {a}ರಿಂದ {b}ಕ್ಕೆ ಏರಬಹುದು', try_msg_gv: 'ನಿಮ್ಮ ಶುಗರ್ ಏರಿಳಿತಗಳು ಸುಮಾರು {n}% ಕಡಿಮೆಯಾಗಬಹುದು',
  try_msg_liver: ', ಮತ್ತು ಒಂದು ವರ್ಷದಲ್ಲಿ ಯಕೃತ್ತಿನಲ್ಲಿ ಕೊಬ್ಬು ಶೇಖರಣೆಯ ಸಾಧ್ಯತೆ {a}ರಿಂದ {b}ಕ್ಕೆ ಇಳಿಯಬಹುದು.',
  try_note: 'ಇದು ನಿರ್ಧಾರಕ್ಕೆ ಸಹಾಯ ಮಾಡುವ ಸಿಮ್ಯುಲೇಶನ್ ಮಾತ್ರ, ಭರವಸೆಯಲ್ಲ. ಚಿಕಿತ್ಸೆ ಬದಲಿಸುವ ಮುನ್ನ ನಿಮ್ಮ ವೈದ್ಯರೊಂದಿಗೆ ಮಾತನಾಡಿ.',
  ask_title: 'ಕೇಯಾಗೆ ಕೇಳಿ', ask_hello: 'ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಶುಗರ್, ಸ್ಕ್ರೀನ್\u200cಗಳು ಅಥವಾ ಆ್ಯಪ್ ಬಳಸುವ ಬಗ್ಗೆ ಏನು ಬೇಕಾದರೂ ಕೇಳಿ. ನೀವು ಟೈಪ್ ಮಾಡಬಹುದು ಅಥವಾ ಮೈಕ್ರೋಫೋನ್ ಒತ್ತಬಹುದು.', ask_error: 'ನಾನು ಈಗ ಉತ್ತರಿಸಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', ask_nothing: 'ಏನೂ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.', ask_mic_error: 'ರೆಕಾರ್ಡಿಂಗ್ ಅರ್ಥವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.', ask_no_mic: 'ಈ ಸಾಧನದಲ್ಲಿ ಮೈಕ್ರೋಫೋನ್ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.', ask_mic_denied: 'ಕೇಯಾ ಜೊತೆ ಮಾತನಾಡಲು ದಯವಿಟ್ಟು ಮೈಕ್ರೋಫೋನ್ ಅನುಮತಿ ನೀಡಿ.', ask_thinking: 'ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ…', ask_stop: 'ರೆಕಾರ್ಡಿಂಗ್ ನಿಲ್ಲಿಸಿ', ask_speak: 'ಮಾತನಾಡಿ', ask_listening: 'ಕೇಳುತ್ತಿದ್ದೇನೆ… ಮುಗಿದ ಮೇಲೆ ■ ಒತ್ತಿ', ask_placeholder: 'ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಹೇಳಿ', send: 'ಕಳುಹಿಸಿ', close: 'ಮುಚ್ಚಿ', read_aloud: 'ಗಟ್ಟಿಯಾಗಿ ಓದಿ', ask_note: 'ನಿಮ್ಮ ಡೇಟಾ ಆಧಾರಿತ ಸಾಮಾನ್ಯ ಮಾರ್ಗದರ್ಶನ, ವೈದ್ಯಕೀಯ ಸಲಹೆ ಅಲ್ಲ.', ask_s1: 'ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ಸಮಯ ಎಂದರೇನು?', ask_s2: 'ನನ್ನ ಶುಗರ್ ಏಕೆ ಹೆಚ್ಚಾಗಿದೆ?', ask_s3: 'ನನ್ನ ಕಿಡ್ನಿ ತೋರಿಸಿ', ask_s4: 'ಭಾಷೆ ಹೇಗೆ ಬದಲಿಸುವುದು?',   hello: 'ನಮಸ್ಕಾರ, {name}', day_good: 'ಒಳ್ಳೆಯ ದಿನ', day_ok: 'ಸಾಮಾನ್ಯ ದಿನ', day_tough: 'ಕಷ್ಟದ ದಿನ', day_sub: 'ದಿನದ {pct} ಸಮಯ ನಿಮ್ಮ ಶುಗರ್ ಸಾಮಾನ್ಯ ವ್ಯಾಪ್ತಿಯಲ್ಲಿತ್ತು.', day_spike: 'ದೊಡ್ಡ ಏರಿಕೆ: {time}ಕ್ಕೆ {v}, ಸುಮಾರು {g} ಗ್ರಾಂ ಊಟದ {m} ನಿಮಿಷಗಳ ನಂತರ.', day_spike_nomeal: 'ಅತಿ ಹೆಚ್ಚು ಶುಗರ್: {time}ಕ್ಕೆ {v}.', day_low: 'ಶುಗರ್ {m} ನಿಮಿಷ ಕಡಿಮೆ ಇತ್ತು', day_nolow: 'ಶುಗರ್ ಇಳಿಯಲಿಲ್ಲ', day_chart: 'ದಿನವಿಡೀ ನಿಮ್ಮ ಶುಗರ್', what_happened: 'ಏನಾಯಿತು',
  read_screen: 'ಈ ಪರದೆಯನ್ನು ಗಟ್ಟಿಯಾಗಿ ಓದಿ', ask_fab: 'ಕೇಳಿ', large_text: 'ದೊಡ್ಡ ಅಕ್ಷರ',
  loading: 'ಲೋಡ್ ಆಗುತ್ತಿದೆ…', lang_note: 'ಹಿಂದಿ, ತೆಲುಗು ಮತ್ತು ಕನ್ನಡ ಅನುವಾದಗಳು ಸ್ಥಳೀಯ ಭಾಷಾ ತಜ್ಞರ ಪರಿಶೀಲನೆಯವರೆಗೆ ಕರಡುಗಳು.',
}

// Doctor messages and prescriptions (the doctor's own text is shown as written, not translated)
Object.assign(en, {
  msg_urgent: 'Urgent message from your doctor', msg_advice: 'Message from your doctor', msg_seen: 'I have seen this',
  msg_act_clinic: 'Please come to the clinic today.', msg_act_er: 'Please go to the nearest emergency room now.', msg_act_call: 'Please call the clinic.',
  msg_past: 'Earlier messages', rx_title: 'Your doctor changed your medicines', rx_note_title: "Doctor's note",
  rx_start: 'Start', rx_stop: 'Stop', rx_dose: 'Change dose', rx_ok: 'Got it, show me my reports',
})
Object.assign(hi, {
  msg_urgent: 'डॉक्टर का ज़रूरी संदेश', msg_advice: 'डॉक्टर का संदेश', msg_seen: 'मैंने देख लिया',
  msg_act_clinic: 'कृपया आज ही क्लिनिक आएँ।', msg_act_er: 'कृपया अभी नज़दीकी इमरजेंसी में जाएँ।', msg_act_call: 'कृपया क्लिनिक को फ़ोन करें।',
  msg_past: 'पिछले संदेश', rx_title: 'आपके डॉक्टर ने आपकी दवाएँ बदली हैं', rx_note_title: 'डॉक्टर का नोट',
  rx_start: 'शुरू करें', rx_stop: 'बंद करें', rx_dose: 'खुराक बदलें', rx_ok: 'समझ गया, मेरी रिपोर्ट दिखाएँ',
})
Object.assign(te, {
  msg_urgent: 'డాక్టర్ నుండి అత్యవసర సందేశం', msg_advice: 'డాక్టర్ నుండి సందేశం', msg_seen: 'నేను చూశాను',
  msg_act_clinic: 'దయచేసి ఈ రోజే క్లినిక్‌కు రండి.', msg_act_er: 'దయచేసి వెంటనే దగ్గరలోని అత్యవసర విభాగానికి వెళ్ళండి.', msg_act_call: 'దయచేసి క్లినిక్‌కు ఫోన్ చేయండి.',
  msg_past: 'ఇంతకు ముందు సందేశాలు', rx_title: 'మీ డాక్టర్ మీ మందులను మార్చారు', rx_note_title: 'డాక్టర్ గమనిక',
  rx_start: 'మొదలుపెట్టండి', rx_stop: 'ఆపండి', rx_dose: 'మోతాదు మార్చండి', rx_ok: 'అర్థమైంది, నా రిపోర్టులు చూపించు',
})
Object.assign(kn, {
  msg_urgent: 'ವೈದ್ಯರಿಂದ ತುರ್ತು ಸಂದೇಶ', msg_advice: 'ವೈದ್ಯರ ಸಂದೇಶ', msg_seen: 'ನಾನು ನೋಡಿದೆ',
  msg_act_clinic: 'ದಯವಿಟ್ಟು ಇಂದೇ ಕ್ಲಿನಿಕ್‌ಗೆ ಬನ್ನಿ.', msg_act_er: 'ದಯವಿಟ್ಟು ಈಗಲೇ ಹತ್ತಿರದ ತುರ್ತು ವಿಭಾಗಕ್ಕೆ ಹೋಗಿ.', msg_act_call: 'ದಯವಿಟ್ಟು ಕ್ಲಿನಿಕ್‌ಗೆ ಕರೆ ಮಾಡಿ.',
  msg_past: 'ಹಿಂದಿನ ಸಂದೇಶಗಳು', rx_title: 'ನಿಮ್ಮ ವೈದ್ಯರು ನಿಮ್ಮ ಔಷಧಿಗಳನ್ನು ಬದಲಾಯಿಸಿದ್ದಾರೆ', rx_note_title: 'ವೈದ್ಯರ ಟಿಪ್ಪಣಿ',
  rx_start: 'ಪ್ರಾರಂಭಿಸಿ', rx_stop: 'ನಿಲ್ಲಿಸಿ', rx_dose: 'ಪ್ರಮಾಣ ಬದಲಿಸಿ', rx_ok: 'ಅರ್ಥವಾಯಿತು, ನನ್ನ ವರದಿಗಳನ್ನು ತೋರಿಸಿ',
})

const DICT = { en, hi, te, kn }

export function makeT(lang) {
  return (key, vars = {}) => {
    let s = (DICT[lang] && DICT[lang][key]) ?? en[key] ?? key
    for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v)
    return s
  }
}
