/**
 * ===================================================================
 * PRESENTER
 * ===================================================================
 * 役割:
 *   - Model（データ）とView（画面）の橋渡し
 *   - 「今どの画面にいるか」「どのモードか」などUIの一時的な状態を保持
 *   - ユーザー操作 → Modelの呼び出し → Viewへの再描画、という一連の
 *     アプリケーションロジックをここに集約する
 *
 * ModelはDOMを知らず、ViewはAPI通信やビジネスロジックを知らない。
 * その間を取り持つのがPresenterの役割。
 * ===================================================================
 */

class IronLogPresenter {
  constructor(model, view) {
    this.model = model;
    this.view = view;

    // ---- UIの一時的な状態（サーバーには保存しない、画面遷移用の状態） ----
    this.selectedDate = null;       // "2026-08-05"
    this.viewYear = null;
    this.viewMonth = null;          // 0-11
    this.currentPart = null;
    this.pickerMode = null;         // "add" | "remove"
    this.visibleInputs = new Set();       // "日付|種目" → 新規セット入力欄を表示中
    this.hiddenActionButtons = new Set(); // "日付|種目" → 削除/追加ボタンを非表示中
  }

  async init() {
    try {
      await this.model.loadAll();
    } catch (err) {
      this.view.showFatalError(err.message);
      return;
    }

    const today = new Date();
    this.viewYear = today.getFullYear();
    this.viewMonth = today.getMonth();

    this.view.renderLegend(this.model.PART_COLORS);
    this.renderCalendar();
    this.view.renderBodyParts(this.model.bodyParts, (part) => this.selectBodyPart(part));
    this.bindStaticEvents();
    this.showView("calendar");
  }

  // ---------------- 画面切り替え＋パンくず ----------------

  showView(name) {
    this.view.showView(name);
    this.view.renderCrumbs(
      name,
      {
        selectedDateLabel: this.selectedDate ? IronLogView.formatDateLabel(this.selectedDate) : null,
        currentPart: this.currentPart,
        pickerMode: this.pickerMode,
      },
      (target) => this.handleCrumbNav(target)
    );
  }

  handleCrumbNav(target) {
    if (target === "calendar") this.showView("calendar");
    if (target === "history" && this.selectedDate) {
      this.renderHistory();
      this.showView("history");
    }
    if (target === "parts" && this.selectedDate) this.showView("parts");
  }

  // ---------------- カレンダー ----------------

  renderCalendar() {
    const y = this.viewYear;
    const m = this.viewMonth;
    const firstDay = new Date(y, m, 1);
    const startWeekday = firstDay.getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const today = new Date();
    const todayStr = IronLogView.dateKey(today.getFullYear(), today.getMonth(), today.getDate());

    const days = [];
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = IronLogView.dateKey(y, m, d);
      days.push({
        day: d,
        dateStr,
        isToday: dateStr === todayStr,
        isSelected: dateStr === this.selectedDate,
        trainedParts: this.model.partsTrainedOn(dateStr),
      });
    }

    this.view.renderCalendar(
      { year: y, month: m, startWeekday, days, colors: this.model.PART_COLORS },
      (dateStr) => this.selectDate(dateStr)
    );
  }

  selectDate(dateStr) {
    this.selectedDate = dateStr;
    this.view.setSelectedDateBanner(`${IronLogView.formatDateLabel(dateStr)} の記録`);
    this.renderCalendar();
    this.renderHistory();
    this.showView("history");
  }

  // ---------------- 部位選択 ----------------

  selectBodyPart(part) {
    this.currentPart = part;
    this.renderExercisePicker();
    this.showView("exercises");
  }

  // ---------------- トレーニング履歴一覧 ----------------

  renderHistory() {
    this.view.setHistoryHeading(
      this.selectedDate ? `${IronLogView.formatDateLabel(this.selectedDate)} の履歴` : "トレーニング履歴"
    );

    const list = this.model.allExercisesForDate(this.selectedDate);

    const items = list.map(({ exercise, part }) => {
      const sets = this.model.setsForExerciseOnDate(exercise, this.selectedDate);
      const inputKey = `${this.selectedDate}|${exercise}`;
      return {
        exercise,
        part,
        color: this.model.PART_COLORS[part],
        sets,
        bestWeight: this.model.bestWeightSet(exercise),
        bestReps: this.model.bestRepsSet(exercise),
        note: this.model.getNote(exercise),
        isInputVisible: this.visibleInputs.has(inputKey),
        areActionsHidden: this.hiddenActionButtons.has(inputKey),
      };
    });

    this.view.renderHistory(items, {
      deleteExercise: (part, exercise) => this.removeDayExercise(part, exercise),
      saveNote: (exercise, value) => this.saveNote(exercise, value),
      deleteSet: (part, exercise, idx) => this.deleteSetInline(part, exercise, idx),
      addSet: (part, exercise, weightStr, repsStr, checkboxEl, errorEl) =>
        this.addSetInline(part, exercise, weightStr, repsStr, checkboxEl, errorEl),
      showInputRow: (exercise) => {
        this.visibleInputs.add(`${this.selectedDate}|${exercise}`);
      },
      hideActionsRow: (exercise) => {
        this.hiddenActionButtons.add(`${this.selectedDate}|${exercise}`);
      },
      showActionsRow: (exercise) => {
        this.hiddenActionButtons.delete(`${this.selectedDate}|${exercise}`);
      },
      removeLastSet: (part, exercise, sets) => {
        if (sets.length === 0) {
          window.alert("削除できるセットがありません。");
          return;
        }
        const lastSet = sets[sets.length - 1];
        this.deleteSetInline(part, exercise, lastSet._idx);
      },
    });
  }

  /** Modelの更新系メソッド呼び出し＋失敗時のアラート表示、という繰り返しパターンの共通処理 */
  async _runAction(action) {
    try {
      await action();
    } catch (err) {
      window.alert(err.message);
    }
  }

  /** セット・種目の増減があった後、カレンダーと履歴を両方再描画する */
  _refreshCalendarAndHistory() {
    this.renderHistory();
    this.renderCalendar();
  }

  async saveNote(exercise, note) {
    await this._runAction(() => this.model.saveNote(exercise, note));
  }

  async addSetInline(part, exercise, weightRaw, repsRaw, checkbox, errorEl) {
    errorEl.hidden = true;

    const weight = parseFloat(weightRaw);
    const reps = parseInt(repsRaw, 10);

    if (Number.isNaN(weight) || weight < 0) {
      errorEl.textContent = "重量を正しく入力してください。";
      errorEl.hidden = false;
      checkbox.checked = false;
      return;
    }
    if (Number.isNaN(reps) || reps <= 0) {
      errorEl.textContent = "回数は1以上の整数で入力してください。";
      errorEl.hidden = false;
      checkbox.checked = false;
      return;
    }

    try {
      await this.model.addSet(exercise, weight, reps, this.selectedDate);
      this.visibleInputs.delete(`${this.selectedDate}|${exercise}`);
      this._refreshCalendarAndHistory();
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
      checkbox.checked = false;
    }
  }

  async deleteSetInline(part, exercise, index) {
    await this._runAction(async () => {
      await this.model.deleteSet(exercise, index);
      this._refreshCalendarAndHistory();
    });
  }

  async addDayExercise(part, exercise) {
    await this._runAction(async () => {
      await this.model.addDayExercise(this.selectedDate, part, exercise);
      this.renderHistory();
      this.showView("history");
    });
  }

  async removeDayExercise(part, exercise) {
    await this._runAction(async () => {
      await this.model.removeDayExercise(this.selectedDate, part, exercise);
      this._refreshCalendarAndHistory();
      this.showView("history");
    });
  }

  // ---------------- 種目選択（追加 / 削除モード） ----------------

  renderExercisePicker() {
    const isRemoveMode = this.pickerMode === "remove";
    const part = this.currentPart;

    // 部位を経由しない「履歴」直接の削除モード：全部位横断で選ぶ
    if (isRemoveMode && !part) {
      this.view.setExerciseViewHeading("削除する種目を選ぶ");
      const allAdded = this.model.allExercisesForDate(this.selectedDate);

      const items = allAdded.map(({ exercise, part: exPart }) => {
        const sets = this.model.allSets[exercise] || [];
        const lastSet = sets[sets.length - 1];
        const meta = lastSet
          ? `${exPart} ・ 直近 ${lastSet.weight}kg×${lastSet.reps} / ${sets.length}セット`
          : `${exPart} ・ 記録なし`;
        return { exercise, part: exPart, label: exercise, meta };
      });

      this.view.renderExercisePicker(
        items,
        (item) => this.removeDayExercise(item.part, item.exercise),
        "削除できる種目がありません。"
      );
      return;
    }

    const already = this.model.exercisesForDate(this.selectedDate, part);
    // 追加モードでは全種目を常に表示する（追加済みでも一覧から消さず、再選択できるようにする）
    const candidates = isRemoveMode ? already : this.model.bodyParts[part];

    this.view.setExerciseViewHeading(
      isRemoveMode ? `${part}：削除する種目を選ぶ` : `${part}：追加する種目を選ぶ`
    );

    const items = candidates.map((exercise) => {
      const sets = this.model.allSets[exercise] || [];
      const lastSet = sets[sets.length - 1];
      const meta = lastSet
        ? `直近 ${lastSet.weight}kg×${lastSet.reps} / ${sets.length}セット`
        : "記録なし";
      const addedTag = !isRemoveMode && already.includes(exercise) ? "（追加済み）" : "";
      return { exercise, part, label: `${exercise}${addedTag}`, meta };
    });

    this.view.renderExercisePicker(
      items,
      (item) => {
        if (isRemoveMode) {
          this.removeDayExercise(part, item.exercise);
        } else {
          this.addDayExercise(part, item.exercise);
        }
      },
      "削除できる種目がありません。"
    );
  }

  // ---------------- 全記録モーダル ----------------

  openAllRecordsModal() {
    const exercises = Object.keys(this.model.allSets).filter(
      (ex) => this.model.allSets[ex] && this.model.allSets[ex].length > 0
    );
    const groups = exercises.map((exercise) => ({ exercise, sets: this.model.allSets[exercise] }));
    this.view.openAllRecordsModal(groups);
  }

  // ---------------- 静的なイベント配線（1回だけ登録） ----------------

  bindStaticEvents() {
    this.view.bindCalendarNav({
      onPrev: () => {
        this.viewMonth -= 1;
        if (this.viewMonth < 0) {
          this.viewMonth = 11;
          this.viewYear -= 1;
        }
        this.renderCalendar();
      },
      onNext: () => {
        this.viewMonth += 1;
        if (this.viewMonth > 11) {
          this.viewMonth = 0;
          this.viewYear += 1;
        }
        this.renderCalendar();
      },
      onToday: () => {
        const today = new Date();
        this.viewYear = today.getFullYear();
        this.viewMonth = today.getMonth();
        this.renderCalendar();
        this.selectDate(IronLogView.dateKey(today.getFullYear(), today.getMonth(), today.getDate()));
      },
    });

    this.view.bindHistoryActions({
      onAddExercise: () => {
        this.pickerMode = "add";
        this.currentPart = null;
        this.showView("parts");
      },
      onRemoveExercise: () => {
        this.pickerMode = "remove";
        this.currentPart = null;
        this.renderExercisePicker();
        this.showView("exercises");
      },
    });

    this.view.bindNavButtons({
      onBackToCalendar: () => {
        this.renderCalendar();
        this.showView("calendar");
      },
      onBackToHistoryFromParts: () => {
        this.renderHistory();
        this.showView("history");
      },
      onBackFromExercises: () => {
        if (this.pickerMode === "add") {
          this.showView("parts");
        } else {
          this.renderHistory();
          this.showView("history");
        }
      },
    });

    this.view.bindModal({
      onOpen: () => this.openAllRecordsModal(),
      onClose: () => this.view.closeAllRecordsModal(),
    });
  }
}
