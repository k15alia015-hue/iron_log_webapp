/**
 * ===================================================================
 * MODEL
 * ===================================================================
 * 役割:
 *   - サーバーとの通信（fetch）
 *   - アプリのデータそのものの保持（部位/種目/セット/メモなど）
 *   - データに対する問い合わせ・計算ロジック（DOMには一切触れない）
 *
 * View・Presenterからは、このModelのメソッドを呼ぶだけでデータの
 * 取得・更新ができる。DOM操作や画面遷移の知識はここには持たせない。
 * ===================================================================
 */

class IronLogModel {
  constructor() {
    // 部位ごとの色分け（カレンダー・履歴バッジで使う「データ」としての色定義）
    this.PART_COLORS = {
      "胸": "#c1443b",
      "背中": "#4c9a6b",
      "脚": "#4d7a97",
      "肩": "#e0793a",
      "腕": "#d9b23c",
      "腹": "#8b5fbf",
    };

    this.bodyParts = {};     // { "胸": ["ベンチプレス", ...], ... }
    this.allSets = {};       // { "ベンチプレス": [ {weight, reps, date}, ... ], ... }
    this.dayExercises = {};  // { "2026-08-05": [ {part, exercise}, ... ], ... }
    this.exerciseNotes = {}; // { "ベンチプレス": "メモの内容", ... }
    this.exerciseToPart = {}; // { "ベンチプレス": "胸", ... }
  }

  // ---------------- 通信ヘルパー ----------------

  async _fetchJSON(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || "サーバーとの通信に失敗しました");
    }
    return data;
  }

  // ---------------- 初期読み込み ----------------

  async loadAll() {
    const [bodyParts, allSets, dayExercises, exerciseNotes] = await Promise.all([
      this._fetchJSON("/api/body-parts"),
      this._fetchJSON("/api/sets"),
      this._fetchJSON("/api/day-exercises"),
      this._fetchJSON("/api/exercise-notes"),
    ]);

    this.bodyParts = bodyParts;
    this.allSets = allSets;
    this.dayExercises = dayExercises;
    this.exerciseNotes = exerciseNotes;

    this.exerciseToPart = {};
    Object.keys(bodyParts).forEach((part) => {
      bodyParts[part].forEach((exercise) => {
        this.exerciseToPart[exercise] = part;
      });
    });
  }

  // ---------------- 問い合わせ（読み取り専用のロジック） ----------------

  /** その日にトレーニングした部位の一覧（記録済みセットの date から逆算） */
  partsTrainedOn(dateStr) {
    const parts = new Set();
    Object.keys(this.allSets).forEach((exercise) => {
      const part = this.exerciseToPart[exercise];
      if (!part) return;
      const sets = this.allSets[exercise] || [];
      if (sets.some((s) => s.date === dateStr)) {
        parts.add(part);
      }
    });
    return Array.from(parts);
  }

  /** 指定日・指定部位で「追加済み」の種目名一覧（追加した順のまま） */
  exercisesForDate(dateStr, part) {
    const dayList = this.dayExercises[dateStr] || [];
    const explicit = dayList.filter((e) => e.part === part).map((e) => e.exercise);
    const inferred = (this.bodyParts[part] || []).filter(
      (ex) =>
        !explicit.includes(ex) &&
        (this.allSets[ex] || []).some((s) => s.date === dateStr)
    );
    return [...explicit, ...inferred];
  }

  /** 指定日に追加済みの全種目を、部位を問わず「追加した順」で横断取得 */
  allExercisesForDate(dateStr) {
    const dayList = this.dayExercises[dateStr] || [];
    const result = dayList.map((e) => ({ exercise: e.exercise, part: e.part }));
    const seen = new Set(dayList.map((e) => e.exercise));

    Object.keys(this.bodyParts).forEach((part) => {
      (this.bodyParts[part] || []).forEach((exercise) => {
        if (seen.has(exercise)) return;
        if ((this.allSets[exercise] || []).some((s) => s.date === dateStr)) {
          result.push({ exercise, part });
          seen.add(exercise);
        }
      });
    });

    return result;
  }

  /** 指定日・指定種目のセット一覧（元配列でのindexを _idx として保持） */
  setsForExerciseOnDate(exercise, dateStr) {
    return (this.allSets[exercise] || [])
      .map((s, i) => ({ ...s, _idx: i }))
      .filter((s) => s.date === dateStr);
  }

  /** これまでの全記録の中で最も重い重量のセット */
  bestWeightSet(exercise) {
    const sets = this.allSets[exercise] || [];
    if (!sets.length) return null;
    return sets.reduce((best, s) => (s.weight > best.weight ? s : best), sets[0]);
  }

  /** これまでの全記録の中で最も回数が多いセット（同回数なら重量が重い方） */
  bestRepsSet(exercise) {
    const sets = this.allSets[exercise] || [];
    if (!sets.length) return null;
    const maxReps = Math.max(...sets.map((s) => s.reps));
    const candidates = sets.filter((s) => s.reps === maxReps);
    return candidates.reduce((best, s) => (s.weight > best.weight ? s : best), candidates[0]);
  }

  getNote(exercise) {
    return this.exerciseNotes[exercise] || "";
  }

  // ---------------- 更新系（サーバーへ反映してからローカルキャッシュも更新） ----------------

  async addSet(exercise, weight, reps, dateStr) {
    const result = await this._fetchJSON("/api/sets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exercise, weight, reps, date: dateStr }),
    });
    this.allSets[exercise] = result.sets;
    return result;
  }

  async deleteSet(exercise, index) {
    const result = await this._fetchJSON(
      `/api/sets/${encodeURIComponent(exercise)}/${index}`,
      { method: "DELETE" }
    );
    if (result.sets && result.sets.length > 0) {
      this.allSets[exercise] = result.sets;
    } else {
      delete this.allSets[exercise];
    }
    return result;
  }

  async addDayExercise(dateStr, part, exercise) {
    const result = await this._fetchJSON("/api/day-exercises", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: dateStr, part, exercise }),
    });
    this.dayExercises[dateStr] = result.list;
    return result;
  }

  async removeDayExercise(dateStr, part, exercise) {
    const result = await this._fetchJSON(
      `/api/day-exercises/${encodeURIComponent(dateStr)}/${encodeURIComponent(part)}/${encodeURIComponent(exercise)}`,
      { method: "DELETE" }
    );
    this.dayExercises[dateStr] = result.list;
    if (result.sets && result.sets.length > 0) {
      this.allSets[exercise] = result.sets;
    } else {
      delete this.allSets[exercise];
    }
    return result;
  }

  async saveNote(exercise, note) {
    const result = await this._fetchJSON("/api/exercise-notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exercise, note }),
    });
    this.exerciseNotes[exercise] = result.note;
    return result;
  }
}
