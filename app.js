let questions = [];
let currentIdx = 0;

async function startQuiz() {
    const chapter = document.getElementById('chapter').value;
    const count = parseInt(document.getElementById('count').value);

    try {
        let query = db.collection('questions'); // 假設你的集合名稱叫 questions
        if (chapter !== 'all') {
            query = query.where('chapter', '==', chapter);
        }

        const snapshot = await query.limit(count).get();
        questions = snapshot.docs.map(doc => doc.data());

        if (questions.length === 0) {
            alert("找不到題目，請檢查資料庫是否有資料！");
            return;
        }

        document.getElementById('setup').style.display = 'none';
        document.getElementById('quiz').style.display = 'block';
        showQuestion();
    } catch (error) {
        console.error("抓取失敗:", error);
        alert("資料庫讀取失敗，請檢查 Firebase Rules 設定。");
    }
}

function showQuestion() {
    const q = questions[currentIdx];
    document.getElementById('progress').innerText = `第 ${currentIdx + 1} 題 / 共 ${questions.length} 題`;
    document.getElementById('question').innerText = q.text; // 假設欄位叫 text
    
    const optionsDiv = document.getElementById('options');
    optionsDiv.innerHTML = '';
    
    // 假設題目選項存在 q.options 陣列中
    q.options.forEach((opt, index) => {
        const btn = document.createElement('button');
        btn.innerText = opt;
        btn.onclick = () => selectOption(index);
        optionsDiv.appendChild(btn);
    });

    // 判斷按鈕顯示
    if (currentIdx === questions.length - 1) {
        document.getElementById('nextBtn').style.display = 'none';
        document.getElementById('submitBtn').style.display = 'inline-block';
    } else {
        document.getElementById('nextBtn').style.display = 'inline-block';
        document.getElementById('submitBtn').style.display = 'none';
    }
}

function next() {
    currentIdx++;
    showQuestion();
}

function submitQuiz() {
    alert("測驗完成！");
    location.reload(); // 重新整理
}
