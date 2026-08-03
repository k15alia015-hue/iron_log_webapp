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
      confirmBackdrop: document.getElementById("confirm-backdrop"),
      confirmMessage: document.getElementById("confirm-message"),
      confirmYes: document.getElementById("confirm-yes"),
      confirmNo: document.getElementById("confirm-no"),
      timerBackdrop: document.getElementById("timer-backdrop"),
      timerMinutes: document.getElementById("timer-minutes"),
      timerSeconds: document.getElementById("timer-seconds"),
      timerPreview: document.getElementById("timer-preview"),
      timerDisable: document.getElementById("timer-disable"),
      timerCancel: document.getElementById("timer-cancel"),
      timerApply: document.getElementById("timer-apply"),
    };
    this._audioCtx = null; // レスト終了音用（初回のユーザー操作時に生成）
  }

  // ---------------- 時間表示ユーティリティ ----------------

  static REST_MINUTES = [1, 2, 3, 4, 5];
  static REST_SECONDS = [0, 10, 20, 30, 40, 50];

  /** 秒数を "m:ss" 形式にする */
  static formatClock(totalSeconds) {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
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

    items.forEach(({ exercise, part, color, sets, bestWeight, bestReps, note, isInputVisible, areActionsHidden, restSeconds, timerRunning, timerRemaining }) => {
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

      // MAX重量／MAX回数は記録が無くても常に表示し、値が無い部分はダッシュで示す
      const MAX_PLACEHOLDER = "ーーーkg ーー回";
      const maxWeightText = bestWeight ? `${bestWeight.weight}kg ${bestWeight.reps}回` : MAX_PLACEHOLDER;
      const maxRepsText = bestReps ? `${bestReps.weight}kg ${bestReps.reps}回` : MAX_PLACEHOLDER;
      const bestHTML = `
        <div class="hc-best">
          <span class="hc-best-line hc-best-line-max"><span class="hc-best-label">MAX重量</span>${maxWeightText}</span>
          <span class="hc-best-line"><span class="hc-best-label">MAX回数</span>${maxRepsText}</span>
        </div>`;

      const timerHTML = `
        <div class="hc-timer" data-timer-exercise="${IronLogView.escapeHTML(exercise)}">
          <span class="hc-timer-caption">タイマー</span>
          <div class="hc-timer-controls">
            <button type="button" class="hc-timer-label" title="レスト時間の設定">⏱ <span class="hc-timer-text"></span></button>
            <button type="button" class="hc-timer-toggle" title="タイマー開始／停止" hidden>▶</button>
          </div>
        </div>
      `;

      card.innerHTML = `
        <div class="hc-header">
          <span class="h-name"><span class="h-part-dot" style="background:${color}"></span><span class="h-name-text">${IronLogView.escapeHTML(exercise)}</span></span>
          <div class="hc-header-right">
            ${timerHTML}
            ${bestHTML}
            <button class="btn-history-delete" title="この種目を削除">×</button>
          </div>
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

      // レストタイマー：ラベルで設定、トグルで開始/停止。初期表示を反映する。
      const timerBox = card.querySelector(".hc-timer");
      timerBox.querySelector(".hc-timer-label").addEventListener("click", () => handlers.editTimer(exercise));
      timerBox.querySelector(".hc-timer-toggle").addEventListener("click", () => handlers.toggleTimer(exercise));
      this._applyTimerState(timerBox, { restSeconds, running: timerRunning, remaining: timerRemaining });

      this.el.historyList.appendChild(card);
    });
  }

  // ---------------- レストタイマー表示 ----------------

  /** タイマー1つ分の見た目（ラベル文字・トグル・状態クラス）を反映する */
  _applyTimerState(container, { restSeconds, running, remaining, done }) {
    const textEl = container.querySelector(".hc-timer-text");
    const toggle = container.querySelector(".hc-timer-toggle");

    container.classList.toggle("is-off", !restSeconds);
    container.classList.toggle("is-running", !!running);
    container.classList.toggle("is-done", !!done);

    if (!restSeconds) {
      textEl.textContent = "不使用";
      toggle.hidden = true;
      return;
    }
    toggle.hidden = false;
    toggle.textContent = running ? "■" : "▶";
    if (done) {
      textEl.textContent = "終了";
    } else {
      textEl.textContent = IronLogView.formatClock(running ? remaining : restSeconds);
    }
  }

  /** Presenterのカウントダウンから呼ばれ、該当種目のタイマー表示だけを更新する */
  updateRestTimer(exercise, state) {
    const container = this.el.historyList.querySelector(
      `.hc-timer[data-timer-exercise="${CSS.escape(exercise)}"]`
    );
    if (container) this._applyTimerState(container, state);
  }

  /** レスト終了の通知：ビープ音を鳴らし、少し「終了」表示にしてから元の設定値へ戻す */
  notifyRestDone(exercise, restSeconds) {
    this._playBeep();
    setTimeout(() => {
      this.updateRestTimer(exercise, { restSeconds, running: false });
    }, 3000);
  }

  /** レスト終了音を出せるよう、ユーザー操作のタイミングでAudioContextを準備する */
  primeAudio() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      if (!this._audioCtx) this._audioCtx = new Ctx();
      if (this._audioCtx.state === "suspended") this._audioCtx.resume();
    } catch (_e) {
      /* 音が出せない環境は無視 */
    }
  }

  _playBeep() {
    try {
      const ctx = this._audioCtx || (this._audioCtx = new (window.AudioContext || window.webkitAudioContext)());
      const now = ctx.currentTime;
      [0, 0.25, 0.5].forEach((offset) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = 880;
        osc.connect(gain);
        gain.connect(ctx.destination);
        gain.gain.setValueAtTime(0.0001, now + offset);
        gain.gain.exponentialRampToValueAtTime(0.3, now + offset + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.18);
        osc.start(now + offset);
        osc.stop(now + offset + 0.2);
      });
    } catch (_e) {
      /* 音が出せない環境は無視 */
    }
  }

  /**
   * レスト時間の設定ポップアップを開く。
   * 「設定」で選んだ秒数、「不使用」で0、「キャンセル/閉じる」でnullを返すPromise。
   */
  openTimerSettings(currentRestSeconds) {
    let selMin = null;
    let selSec = null;
    if (currentRestSeconds > 0) {
      selMin = Math.floor(currentRestSeconds / 60);
      selSec = currentRestSeconds % 60;
    }

    return this._openModal(this.el.timerBackdrop, ({ close, on }) => {
      // 0秒も有効な選択なので、未選択(null)かどうかで判定する
      const bothSelected = () => selMin !== null && selSec !== null;

      const refresh = () => {
        if (bothSelected()) {
          const secLabel = String(selSec).padStart(2, "0");
          this.el.timerPreview.textContent = `${selMin}分${secLabel}秒（${IronLogView.formatClock(selMin * 60 + selSec)}）`;
          this.el.timerApply.disabled = false;
        } else {
          this.el.timerPreview.textContent = "分と秒を選択してください";
          this.el.timerApply.disabled = true;
        }
      };

      const buildOptions = (containerEl, values, getSelected, setSelected) => {
        containerEl.innerHTML = "";
        values.forEach((value) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "timer-option";
          btn.textContent = value;
          if (getSelected() === value) btn.classList.add("is-selected");
          btn.addEventListener("click", () => {
            setSelected(value);
            containerEl.querySelectorAll(".timer-option").forEach((b) => b.classList.remove("is-selected"));
            btn.classList.add("is-selected");
            refresh();
          });
          containerEl.appendChild(btn);
        });
      };

      buildOptions(this.el.timerMinutes, IronLogView.REST_MINUTES, () => selMin, (v) => { selMin = v; });
      buildOptions(this.el.timerSeconds, IronLogView.REST_SECONDS, () => selSec, (v) => { selSec = v; });
      refresh();

      on(this.el.timerApply, "click", () => { if (bothSelected()) close(selMin * 60 + selSec); });
      on(this.el.timerDisable, "click", () => close(0));
      on(this.el.timerCancel, "click", () => close(null));
      return null; // Escape・背景クリック = キャンセル
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
   * 種目名フォーム共通の送信処理：空チェック → 非同期送信 → 失敗時のみエラー表示。
   * 追加フォームと名前変更フォームで共有する。
   * 成功時は一覧全体が再描画されるので、呼び出し側での後処理は不要。
   */
  async _submitExerciseName(rawValue, errorEl, onSubmit) {
    const name = rawValue.trim();
    errorEl.hidden = true;
    if (!name) {
      errorEl.textContent = "種目名を入力してください。";
      errorEl.hidden = false;
      return;
    }
    try {
      await onSubmit(name);
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    }
  }

  /**
   * items: [{ exercise, part, label, meta, editable }, ...]
   * handlers: {
   *   onSelect(item),                       … 通常時、行クリックで種目を選ぶ
   *   emptyMessage,                         … 一覧が空のときの文言
   *   onAddExercise(name),                  … 指定すると一覧の下に「種目の追加」UIを出す
   *   editMode,                             … true のとき編集モードで描画する
   *   onEditToggle(),                       … 「種目の編集」ボタン押下
   *   onRename(part, oldName, newName),     … 編集モードで名前変更（失敗時throwでフォームに表示）
   *   onDelete(part, exercise),             … 編集モードで削除（確認ダイアログ込み）
   * }
   */
  renderExercisePicker(items, handlers = {}) {
    const { onSelect, emptyMessage, onAddExercise, editMode, onEditToggle, onRename, onDelete } = handlers;
    this.el.exerciseList.innerHTML = "";

    const wrap = document.createElement("div");
    wrap.style.display = "flex";
    wrap.style.flexDirection = "column";
    wrap.style.gap = "8px";

    if (items.length === 0) {
      const msg = document.createElement("p");
      msg.className = "empty-state";
      msg.textContent = emptyMessage || "選択できる種目がありません。";
      wrap.appendChild(msg);
    }

    items.forEach((item) => {
      if (editMode && item.editable) {
        wrap.appendChild(this._buildEditableExerciseRow(item, onRename, onDelete));
      } else if (editMode) {
        wrap.appendChild(this._buildStaticExerciseRow(item));
      } else {
        wrap.appendChild(this._buildSelectableExerciseRow(item, onSelect));
      }
    });

    if (onAddExercise) {
      wrap.appendChild(this._buildAddExerciseForm(onAddExercise));
    }
    if (onEditToggle) {
      wrap.appendChild(this._buildEditToggle(editMode, onEditToggle));
    }

    this.el.exerciseList.appendChild(wrap);
  }

  /** 通常モードの、クリックで選択できる種目行 */
  _buildSelectableExerciseRow(item, onSelect) {
    const el = document.createElement("button");
    el.className = "exercise-item";
    el.innerHTML = `
      <span class="ex-name">${IronLogView.escapeHTML(item.label)}</span>
      <span class="ex-meta">${IronLogView.escapeHTML(item.meta)}</span>
    `;
    el.addEventListener("click", () => onSelect(item));
    return el;
  }

  /** 編集モードで、編集できない（初期）種目を表示するだけの行 */
  _buildStaticExerciseRow(item) {
    const el = document.createElement("div");
    el.className = "exercise-item is-static";
    el.innerHTML = `
      <span class="ex-name">${IronLogView.escapeHTML(item.exercise)}</span>
      <span class="ex-meta">初期種目</span>
    `;
    return el;
  }

  /** 編集モードで、名前変更・削除ができるユーザー追加種目の行 */
  _buildEditableExerciseRow(item, onRename, onDelete) {
    const row = document.createElement("div");
    row.className = "exercise-item exercise-item-edit";
    row.innerHTML = `
      <div class="ex-edit-line">
        <div class="ex-edit-main">
          <span class="ex-name">${IronLogView.escapeHTML(item.exercise)}</span>
          <input type="text" class="ex-rename-input" maxlength="255" hidden>
        </div>
        <div class="ex-edit-actions">
          <button type="button" class="ex-rename-btn">名前の変更</button>
          <button type="button" class="ex-delete-btn">種目の削除</button>
          <button type="button" class="ex-rename-save" hidden>保存</button>
          <button type="button" class="ex-rename-cancel" hidden>キャンセル</button>
        </div>
      </div>
      <p class="ex-edit-error" hidden></p>
    `;

    const nameLabel = row.querySelector(".ex-name");
    const input = row.querySelector(".ex-rename-input");
    const renameBtn = row.querySelector(".ex-rename-btn");
    const deleteBtn = row.querySelector(".ex-delete-btn");
    const saveBtn = row.querySelector(".ex-rename-save");
    const cancelBtn = row.querySelector(".ex-rename-cancel");
    const errorEl = row.querySelector(".ex-edit-error");

    const showRenameMode = (on) => {
      nameLabel.hidden = on;
      input.hidden = !on;
      renameBtn.hidden = on;
      deleteBtn.hidden = on;
      saveBtn.hidden = !on;
      cancelBtn.hidden = !on;
      errorEl.hidden = true;
      if (on) {
        input.value = item.exercise;
        input.focus();
        input.select();
      }
    };

    const submit = () =>
      this._submitExerciseName(input.value, errorEl, (name) => onRename(item.part, item.exercise, name));

    renameBtn.addEventListener("click", () => showRenameMode(true));
    cancelBtn.addEventListener("click", () => showRenameMode(false));
    saveBtn.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
      if (e.key === "Escape") showRenameMode(false);
    });
    deleteBtn.addEventListener("click", () => onDelete(item.part, item.exercise));

    return row;
  }

  /** 「種目の編集」トグルボタン */
  _buildEditToggle(editMode, onEditToggle) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "edit-exercise-toggle" + (editMode ? " is-active" : "");
    btn.textContent = editMode ? "編集を終了" : "✎ 種目の編集";
    btn.addEventListener("click", onEditToggle);
    return btn;
  }

  /**
   * モーダル共通処理。背景の表示、Escape・背景クリックでのキャンセル、後片付けをまとめる。
   * setup({ close, on }) でモーダル固有の中身（ボタン配線など）を組み立て、
   * Escape・背景クリック時に resolve する値（キャンセル値）を返す。
   *   close(value) … 明示的に閉じて value で解決する
   *   on(el, event, handler) … リスナー登録（閉じるとき自動で解除される）
   */
  _openModal(backdropEl, setup) {
    return new Promise((resolve) => {
      const cleanups = [];
      const on = (el, event, handler) => {
        el.addEventListener(event, handler);
        cleanups.push(() => el.removeEventListener(event, handler));
      };
      const close = (value) => {
        backdropEl.hidden = true;
        cleanups.forEach((fn) => fn());
        resolve(value);
      };
      backdropEl.hidden = false;
      const cancelValue = setup({ close, on });
      on(backdropEl, "click", (e) => { if (e.target === backdropEl) close(cancelValue); });
      on(document, "keydown", (e) => { if (e.key === "Escape") close(cancelValue); });
    });
  }

  /** 「本当に削除してよろしいですか？」の確認ダイアログ。はい→true / いいえ→false を返す */
  confirm(message) {
    this.el.confirmMessage.textContent = message;
    return this._openModal(this.el.confirmBackdrop, ({ close, on }) => {
      on(this.el.confirmYes, "click", () => close(true));
      on(this.el.confirmNo, "click", () => close(false));
      this.el.confirmNo.focus();
      return false; // Escape・背景クリック = いいえ
    });
  }

  /** 「＋ 種目を追加」ボタン → クリックで入力欄が開き、保存するフォーム部品を生成する */
  _buildAddExerciseForm(onAddExercise) {
    const box = document.createElement("div");
    box.className = "add-exercise-box";
    box.innerHTML = `
      <button type="button" class="add-exercise-toggle">＋ 種目を追加</button>
      <div class="add-exercise-form" hidden>
        <input type="text" class="add-exercise-input" placeholder="新しい種目名を入力" maxlength="255">
        <div class="add-exercise-actions">
          <button type="button" class="add-exercise-cancel">キャンセル</button>
          <button type="button" class="add-exercise-save">保存</button>
        </div>
        <p class="add-exercise-error" hidden></p>
      </div>
    `;

    const toggle = box.querySelector(".add-exercise-toggle");
    const form = box.querySelector(".add-exercise-form");
    const input = box.querySelector(".add-exercise-input");
    const cancelBtn = box.querySelector(".add-exercise-cancel");
    const saveBtn = box.querySelector(".add-exercise-save");
    const errorEl = box.querySelector(".add-exercise-error");

    const openForm = () => {
      toggle.hidden = true;
      form.hidden = false;
      errorEl.hidden = true;
      input.value = "";
      input.focus();
    };

    const closeForm = () => {
      form.hidden = true;
      toggle.hidden = false;
    };

    const submit = () => this._submitExerciseName(input.value, errorEl, (name) => onAddExercise(name));

    toggle.addEventListener("click", openForm);
    cancelBtn.addEventListener("click", closeForm);
    saveBtn.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
      if (e.key === "Escape") closeForm();
    });

    return box;
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
