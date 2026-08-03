/**
 * ===================================================================
 * BOOTSTRAP
 * ===================================================================
 * Model / View / Presenter を組み立てて起動するだけのエントリーポイント。
 * アプリケーションロジックはここには書かない（Presenterに集約する）。
 * ===================================================================
 */
(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    const model = new IronLogModel();
    const view = new IronLogView();
    const presenter = new IronLogPresenter(model, view);
    presenter.init();
  });
})();
