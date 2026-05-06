let allQuestions = [];
let quiz = [];
let index = 0;
let answers = [];

async function startQuiz() {
  const chapter = document.getElementById("chapter").value;
  const count = parseInt(document.getElementById("count").value);

  const snapshot = await db.collection("questions").get();
  allQuestions = snapshot.docs.map(doc => doc.data());

  if (chapter !== "all") {
    allQuestions = allQuestions.filter(q => q.chapter === chapter);
  }

  quiz = smartRandom(allQuestions, count);

  document.getElementById("setup").style.display = "none";
  document.getElementById("quiz").style.display = "block";

  showQuestion();
}

function smartRandom(arr, count) {
  const shuffled = arr.sort(() => 0.5 - Math.random());
  return shuffled.slice(0, count);
}

function showQuestion() {
  const q = quiz[index];

  document.getElementById("progress").innerText =
    `${index + 1} / ${quiz.length}`;

  document.getElementById("question").innerText = q.question;

  const optDiv = document.getElementById("options");
  optDiv.innerHTML = "";

  q.options.forEach((opt, i) => {
    const div = document.createElement("div");
    div.className = "option";
    div.innerText = opt;

    if (answers[index] === i) div.classList.add("selected");

    div.onclick = () => {
      answers[index] = i;
      showQuestion();
    };

    optDiv.appendChild(div);
  });
}

function next() {
  if (index < quiz.length - 1) {
    index++;
    showQuestion();
  }
}

function submitQuiz() {
  let score = 0;

  quiz.forEach((q, i) => {
    if (answers[i] === q.answer) score++;
  });

  alert(`分數：${score}/${quiz.length}`);
}
