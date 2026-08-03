/**
 * ===================================================================
 * VIEW
 * ===================================================================
 * 役割:
 *   - DOM要素の参照・描画（render系メソッド）
 *   - ユーザー操作をイベントとしてPresenterに伝える（on系メソッド）
 *
 * Viewはデータの意味（ビジネスロジック）を知らない。Presenterから
 * 渡された「表示用に整形済みのデータ」をそのままDOMに反映するだけ。
 * fetch通信やデータの計算はここには一切書かない。
 * ===================================================================
 */

class IronLogView {
  constructor() {
    this.el = {
      crumbs: document.getElementById("crumbs"),
      viewCalendar: document.getElementById("view-calendar"),
      viewParts: document.getElementById("view-parts"),
      viewHistory: document.getElementById("view-history"),
      viewExercises: document.getElementById("view-exercises"),
      calendarMonthLabel: document.getElementById("calendar-month-label"),
      calendarGrid: document.getElementById("calendar-grid"),
      calPrev: document.getElementById("cal-prev"),
      calNext: document.getElementById("cal-next"),
      btnToday: document.getElementById("btn-today"),
      legend: document.getElementById("legend"),
      backToCalendarFromHistory: document.getElementById("back-to-calendar-from-history"),
      selectedDateBanner: document.getElementById("selected-date-banner"),
      bodyPartGrid: document.getElementById("body-part-grid"),
      backToHistoryFromParts: document.getElementById("back-to-history"),
      historyViewHeading: document.getElementById("history-view-heading"),
      btnAddExercise: document.getElementById("btn-add-exercise"),
      btnRemoveExercise: document.getElementById("btn-remove-exercise"),
      historyList: document.getElementById("history-list"),
      historyEmpty: document.getElementById("history-empty"),
      backFromExercises: document.getElementById("back-to-parts-or-history"),
      exerciseList: document.getElementById("exercise-list"),
      exerciseViewHeading: document.getElementById("exercise-view-heading"),
      btnViewAll: document.getElementById("btn-view-all"),
      modalBackdrop: document.getElementById("modal-backdrop"),
      modalClose: document.getElementById("modal-close"),
      allRecordsBody: document.getElementById("all-records-body"),
    };
  }

  // ---------------- 共通ユーティリティ（表示整形のみ） ----------------

  static escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
  }

  static pad2(n) {
    return String(n).padStart(2, "0");
  }

  static dateKey(y, m, d) {
    return `${y}-${IronLogView.pad2(m + 1)}-${IronLogView.pad2(d)}`;
  }

  static formatDateLabel(dateStr) {
    const [y, m, d] = dateStr.split("-").map(Number);
    return `${y}/${m}/${d}`;
  }

  // ---------------- 画面切り替え ----------------

  showView(name) {
    this.el.viewCalendar.hidden = name !== "calendar";
    this.el.viewParts.hidden = name !== "parts";
    this.el.viewHistory.hidden = name !== "history";
    this.el.viewExercises.hidden = name !== "exercises";
  }

  // ---------------- パンくず ----------------

  renderCrumbs(activeView, { selectedDateLabel, currentPart, pickerMode }, onNavigate) {
    const parts = [];
    parts.push(
      `<button class="crumb ${activeView === "calendar" ? "current" : ""}" data-nav="calendar">カレンダー</button>`
    );
    if (selectedDateLabel) {
      parts.push(`<span class="crumb-sep">/</span>`);
      parts.push(
        `<button class="crumb ${activeView === "history" ? "current" : ""}" data-nav="history">${IronLogView.escapeHTML(selectedDateLabel)}</button>`
      );
    }
    if (activeView === "parts") {
      parts.push(`<span class="crumb-sep">/</span>`);
      parts.push(`<button class="crumb current" data-nav="parts">部位を選ぶ</button>`);
    }
    if (activeView === "exercises") {
      if (currentPart) {
        parts.push(`<span class="crumb-sep">/</span>`);
        parts.push(`<button class="crumb" data-nav="parts">${IronLogView.escapeHTML(currentPart)}</button>`);
      }
      parts.push(`<span class="crumb-sep">/</span>`);
      const label = pickerMode === "remove" ? "種目を削除" : "種目を追加";
      parts.push(`<button class="crumb current" data-nav="exercises">${IronLogView.escapeHTML(label)}</button>`);
    }
    this.el.crumbs.innerHTML = parts.join("");

    this.el.crumbs.querySelectorAll("[data-nav]").forEach((btn) => {
      btn.addEventListener("click", () => onNavigate(btn.dataset.nav));
    });
  }

  // ---------------- カレンダー ----------------

  renderLegend(colors) {
    this.el.legend.innerHTML = Object.keys(colors)
      .map(
        (part) =>
          `<span class="legend-item"><span class="dot" style="background:${colors[part]}"></span>${IronLogView.escapeHTML(part)}</span>`
      )
      .join("");
  }

  /**
   * days: [{ day, dateStr, isToday, isSelected, trainedParts: [part, ...] }, ...]
   */
  renderCalendar({ year, month, startWeekday, days, colors }, onSelectDate) {
    this.el.calendarMonthLabel.textContent = `${year}年${month + 1}月`;
    this.el.calendarGrid.innerHTML = "";

    for (let i = 0; i < startWeekday; i++) {
      const empty = document.createElement("div");
      empty.className = "cal-day cal-day--empty";
      this.el.calendarGrid.appendChild(empty);
    }

    days.forEach(({ day, dateStr, isToday, isSelected, trainedParts }) => {
      const cell = document.createElement("button");
      cell.className = "cal-day";
      if (isToday) cell.classList.add("is-today");
      if (isSelected) cell.classList.add("is-selected");

      const dots = trainedParts
        .map((p) => `<i style="background:${colors[p]}"></i>`)
        .join("");

      cell.innerHTML = `
        <span class="cal-day-num">${day}</span>
        <span class="cal-day-dots">${dots}</span>
      `;
      cell.addEventListener("click", () => onSelectDate(dateStr));
      this.el.calendarGrid.appendChild(cell);
    });
  }

  setSelectedDateBanner(text) {
    this.el.selectedDateBanner.textContent = text;
  }

  bindCalendarNav({ onPrev, onNext, onToday }) {
    this.el.calPrev.addEventListener("click", onPrev);
    this.el.calNext.addEventListener("click", onNext);
    this.el.btnToday.addEventListener("click", onToday);
  }

  // ---------------- 部位選択 ----------------

  renderBodyParts(bodyParts, onSelectPart) {
    this.el.bodyPartGrid.innerHTML = "";
    Object.keys(bodyParts).forEach((part) => {
      const exercises = bodyParts[part];
      const tile = document.createElement("button");
      tile.className = "tile";
      tile.innerHTML = `${IronLogView.escapeHTML(part)}<span class="tile-sub">${exercises.length}種目</span>`;
      tile.addEventListener("click", () => onSelectPart(part));
      this.el.bodyPartGrid.appendChild(tile);
    });
  }

  // ---------------- トレーニング履歴一覧 ----------------

  setHistoryHeading(text) {
    this.el.historyViewHeading.textContent = text;
  }

  setRemoveExerciseDisabled(disabled) {
    this.el.btnRemoveExercise.disabled = disabled;
  }

  /**
   * items: [{
   *   exercise, part, color, sets: [{weight, reps, _idx}],
   *   bestWeight: {weight,reps} | null, bestReps: {weight,reps} | null,
   *   note, isInputVisible, areActionsHidden
   * }, ...]
   *
   * handlers: {
   *   deleteExercise(part, exercise),
   *   saveNote(exercise, value),
   *   deleteSet(part, exercise, idx),
   *   addSet(part, exercise, weightStr, repsStr, checkboxEl, errorEl),
   *   showInputRow(exercise, dateKeyOnly, rowEl),
   *   hideActionsRow(exercise, rowEl),
   *   showActionsRow(exercise, rowEl),
   *   removeLastSet(part, exercise, lastIdx),
   * }
   */
  renderHistory(items, handlers) {
    this.el.historyList.innerHTML = "";
    this.el.historyEmpty.hidden = items.length > 0;
    this.setRemoveExerciseDisabled(items.length === 0);

    items.forEach(({ exercise, part, color, sets, bestWeight, bestReps, note, isInputVisible, areActionsHidden }) => {
      const card = document.createElement("div");
      card.className = "history-card";

      const savedRowsHTML = sets
        .map(
          (s, i) => `
            <div class="hc-set-row" data-idx="${s._idx}">
              <span class="hc-set-num">${i + 1}</span>
              <span class="hc-set-chip">${s.weight}kg</span>
              <span class="hc-set-chip">× ${s.reps}回</span>
              <input type="checkbox" class="hc-set-check" checked title="チェックを外すとこのセットを削除します">
            </div>
          `
        )
        .join("");

      const newRowHTML = `
        <div class="hc-set-row hc-set-row-new" ${isInputVisible ? "" : 'style="display:none"'}>
          <span class="hc-set-num">${sets.length + 1}</span>
          <input type="number" class="hc-weight-inline" inputmode="decimal" step="0.5" min="0" placeholder="重量kg">
          <input type="number" class="hc-reps-inline" inputmode="numeric" step="1" min="1" placeholder="回数">
          <input type="checkbox" class="hc-set-check-new" title="チェックを入れて保存">
        </div>
      `;

      const bestHTML =
        bestWeight && bestReps
          ? `
            <div class="hc-best">
              <span class="hc-best-line hc-best-line-max"><span class="hc-best-label">MAX重量</span>${bestWeight.weight}kg ${bestWeight.reps}回</span>
              <span class="hc-best-line"><span class="hc-best-label">MAX回数</span>${bestReps.weight}kg ${bestReps.reps}回</span>
            </div>
          `
          : "";

      card.innerHTML = `
        <div class="hc-header">
          <span class="h-name"><span class="h-part-dot" style="background:${color}"></span>${IronLogView.escapeHTML(exercise)}</span>
          ${bestHTML}
          <button class="btn-history-delete" title="この種目を削除">×</button>
        </div>
        <div class="hc-memo">
          <textarea class="hc-memo-input" placeholder="メモを入力（前回の内容が残ります）" rows="2">${IronLogView.escapeHTML(note)}</textarea>
        </div>
        <div class="hc-sets">${savedRowsHTML}${newRowHTML}</div>
        <p class="hc-form-error" hidden></p>
        <div class="hc-input-actions hc-set-actions-row" ${areActionsHidden ? 'style="display:none"' : ""}>
          <button type="button" class="hc-set-remove-btn">セットの削除</button>
          <button type="button" class="hc-set-add-btn">セットの追加</button>
        </div>
        <div class="hc-input-actions">
          <button type="button" class="hc-edit-btn">セットの編集</button>
          <button type="button" class="hc-done-btn">セットの完了</button>
        </div>
      `;

      card.querySelector(".btn-history-delete").addEventListener("click", () => handlers.deleteExercise(part, exercise));

      const memoInput = card.querySelector(".hc-memo-input");
      memoInput.addEventListener("blur", () => handlers.saveNote(exercise, memoInput.value));

      card.querySelectorAll(".hc-set-row:not(.hc-set-row-new) .hc-set-check").forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) return; // 既存セットは常にチェック済み。外した時だけ削除
          const idx = Number(checkbox.closest(".hc-set-row").dataset.idx);
          handlers.deleteSet(part, exercise, idx);
        });
      });

      const newRow = card.querySelector(".hc-set-row-new");
      const newCheckbox = newRow.querySelector(".hc-set-check-new");
      const errorEl = card.querySelector(".hc-form-error");
      newCheckbox.addEventListener("change", () => {
        if (!newCheckbox.checked) return;
        const weightInput = newRow.querySelector(".hc-weight-inline");
        const repsInput = newRow.querySelector(".hc-reps-inline");
        handlers.addSet(part, exercise, weightInput.value, repsInput.value, newCheckbox, errorEl);
      });

      const actionsRow = card.querySelector(".hc-set-actions-row");

      card.querySelector(".hc-done-btn").addEventListener("click", () => {
        handlers.hideActionsRow(exercise);
        actionsRow.style.display = "none";
      });

      card.querySelector(".hc-edit-btn").addEventListener("click", () => {
        handlers.showActionsRow(exercise);
        actionsRow.style.display = "";
      });

      card.querySelector(".hc-set-add-btn").addEventListener("click", () => {
        handlers.showInputRow(exercise);
        newRow.style.display = "";
        newRow.querySelector(".hc-weight-inline").focus();
      });

      card.querySelector(".hc-set-remove-btn").addEventListener("click", () => {
        handlers.removeLastSet(part, exercise, sets);
      });

      this.el.historyList.appendChild(card);
    });
  }

  bindHistoryActions({ onAddExercise, onRemoveExercise }) {
    this.el.btnAddExercise.addEventListener("click", onAddExercise);
    this.el.btnRemoveExercise.addEventListener("click", () => {
      if (this.el.btnRemoveExercise.disabled) return;
      onRemoveExercise();
    });
  }

  // ---------------- 種目選択（追加 / 削除モード） ----------------

  setExerciseViewHeading(text) {
    this.el.exerciseViewHeading.textContent = text;
  }

  /**
   * items: [{ exercise, part, label, meta }, ...]
   */
  renderExercisePicker(items, onSelectItem, emptyMessage) {
    this.el.exerciseList.innerHTML = "";

    if (items.length === 0) {
      const msg = document.createElement("p");
      msg.className = "empty-state";
      msg.textContent = emptyMessage || "選択できる種目がありません。";
      this.el.exerciseList.appendChild(msg);
      return;
    }

    const wrap = document.createElement("div");
    wrap.style.display = "flex";
    wrap.style.flexDirection = "column";
    wrap.style.gap = "8px";

    items.forEach((item) => {
      const el = document.createElement("button");
      el.className = "exercise-item";
      el.innerHTML = `
        <span class="ex-name">${IronLogView.escapeHTML(item.label)}</span>
        <span class="ex-meta">${IronLogView.escapeHTML(item.meta)}</span>
      `;
      el.addEventListener("click", () => onSelectItem(item));
      wrap.appendChild(el);
    });

    this.el.exerciseList.appendChild(wrap);
  }

  // ---------------- 全記録モーダル ----------------

  /** groups: [{ exercise, sets: [{weight, reps, date}] }, ...] */
  openAllRecordsModal(groups) {
    if (groups.length === 0) {
      this.el.allRecordsBody.innerHTML = `<p class="empty-state">まだ記録がありません。</p>`;
    } else {
      this.el.allRecordsBody.innerHTML = groups
        .map(({ exercise, sets }) => {
          const rows = sets
            .map(
              (s, i) =>
                `<li><span>${i + 1}. ${s.weight}kg × ${s.reps}</span><span class="d">${s.date}</span></li>`
            )
            .join("");
          return `<div class="all-group"><h4>${IronLogView.escapeHTML(exercise)}</h4><ul>${rows}</ul></div>`;
        })
        .join("");
    }
    this.el.modalBackdrop.hidden = false;
  }

  closeAllRecordsModal() {
    this.el.modalBackdrop.hidden = true;
  }

  bindModal({ onOpen, onClose }) {
    this.el.btnViewAll.addEventListener("click", onOpen);
    this.el.modalClose.addEventListener("click", onClose);
    this.el.modalBackdrop.addEventListener("click", (e) => {
      if (e.target === this.el.modalBackdrop) onClose();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") onClose();
    });
  }

  // ---------------- ナビゲーション（戻るボタン類） ----------------

  bindNavButtons({ onBackToCalendar, onBackToHistoryFromParts, onBackFromExercises }) {
    this.el.backToCalendarFromHistory.addEventListener("click", onBackToCalendar);
    this.el.backToHistoryFromParts.addEventListener("click", onBackToHistoryFromParts);
    this.el.backFromExercises.addEventListener("click", onBackFromExercises);
  }

  showFatalError(message) {
    document.body.innerHTML = `<p style="padding:40px;color:#c1443b;font-family:sans-serif;">初期データの読み込みに失敗しました: ${IronLogView.escapeHTML(message)}</p>`;
  }
}
