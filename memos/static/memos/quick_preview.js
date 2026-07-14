// クイック入力の解析結果を控えめにプレビュー表示する。
// 保存はフォーム送信のまま。JS無効でも従来どおり動作する。
(function () {
  var input = document.getElementById("id_text");
  var preview = document.getElementById("quick-preview");
  if (!input || !preview) {
    return;
  }

  var url = preview.getAttribute("data-preview-url");
  var contentEl = preview.querySelector('[data-role="content"]');
  var reminderEl = preview.querySelector('[data-role="reminder"]');
  var priorityEl = preview.querySelector('[data-role="priority"]');
  var warningEl = preview.querySelector('[data-role="warning"]');
  var timer = null;
  var controller = null;

  function render(data) {
    contentEl.textContent = "本文: " + (data.content || "（なし）");
    reminderEl.textContent = data.has_reminder ? "日時: " + data.reminder : "日時: なし";
    priorityEl.textContent = "優先度: " + (data.priority_display || "未設定");

    if (data.warning) {
      warningEl.textContent = "日時を認識できませんでした（例: 明日18時 / 5月20日）";
      warningEl.hidden = false;
    } else {
      warningEl.hidden = true;
    }

    preview.hidden = false;
  }

  function update() {
    var text = input.value.trim();
    if (!text) {
      preview.hidden = true;
      return;
    }

    if (controller) {
      controller.abort();
    }
    controller = new AbortController();

    fetch(url + "?text=" + encodeURIComponent(text), {
      signal: controller.signal,
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (data) {
        if (data) {
          render(data);
        }
      })
      .catch(function () {
        // 中断・通信失敗時は何もしない（保存操作には影響しない）。
      });
  }

  input.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(update, 250);
  });
})();
