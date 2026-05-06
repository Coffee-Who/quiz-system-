async function addQuestion() {
  const chapter = chapter.value;
  const question = document.getElementById("question").value;
  const options = document.getElementById("options").value.split(",");
  const answer = parseInt(document.getElementById("answer").value);

  await db.collection("questions").add({
    subject: "math",
    chapter,
    question,
    options,
    answer
  });

  alert("新增成功");
}

// PDF解析
async function uploadPDF() {
  const file = document.getElementById("pdfFile").files[0];
  const reader = new FileReader();

  reader.onload = async function () {
    const pdf = await pdfjsLib.getDocument({data: reader.result}).promise;
    let text = "";

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      text += content.items.map(i => i.str).join(" ");
    }

    parse(text);
  };

  reader.readAsArrayBuffer(file);
}

function parse(text) {
  const blocks = text.split(/\d+\./);

  blocks.forEach(b => {
    const parts = b.split(/\(\d\)/);

    if (parts.length >= 5) {
      db.collection("questions").add({
        subject: "math",
        chapter: "PDF匯入",
        question: parts[0],
        options: parts.slice(1,5),
        answer: 0
      });
    }
  });

  alert("PDF匯入完成（需手動修正答案）");
}
