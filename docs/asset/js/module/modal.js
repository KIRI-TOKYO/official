import {setAttributes} from '../helper/setAttributes.js';
import {reflow} from '../helper/reflow.js';
import {ControlTabindex} from '../helper/controlTabindex.js';

/**
 * モーダルダイアログ
 */
export class Modal {
    /**
     * @param {Object} btn - ボタンとなる要素
     * @param {Object} [options] - オプション
     */
    constructor(btn, options = {}) {
        const defaultOptions = {
            template: {
                btnCloseSelector: '.fn-modal_templateBtnClose',
                overlaySelector: '.fn-modal_templateOverlay'
            },
            templateSelector: '.fn-modal_template',
            btnCloseSelector: '.fn-modal_btnClose',
            overlaySelector: '.fn-modal_overlay',
            contentSelector: '.fn-modal_content',
            renderClass: 'is-render',
            showClass: 'is-show',
            hiddenClass: 'is-hidden',
            openClass: 'is-modal-open',
            animateClass: 'is-animate',
            overlay: {
                animateClass: 'is-overlay-animate',
                showClass: 'is-overlay-show',
                hiddenClass: 'is-overlay-hidden'
            }
        };

        this.o = Object.assign(defaultOptions, options);
        this.html = document.querySelector('html');
        this.body = document.querySelector('body');
        this.createTemplate();

        this.btn = btn;
        this.reset();
        this.bind = {};
        this.isAdjustGutter = false;
    }

    /**
     * テンプレートの埋め込み
     * @returns {void}
     */
    createTemplate() {
        if (!document.querySelector(this.o.templateSelector)) {
            fetch('/asset/js/template/modal.html').then((template) => {
                return template.text();
            }).then((template) => {
                this.body.insertAdjacentHTML('beforeend', template);
            });
        }
    }

    /**
     * 初期化
     * @returns {void}
     */
    init() {
        this.btn.setAttribute('role', 'button');
        this.reset();
        this.bindEvent();
    }

    /**
     * メンバ変数をリセット
     * @returns {void}
     */
    reset() {
        this.templateBtnClose = null;
        this.templateOverlay = null;
        this.root = null;
        this.content = null;
        this.title = null;
        this.btnClose = null;
        this.overlay = null;
    }

    /**
     * イベントの登録
     * @returns {void}
     */
    bindEvent() {
        this.btn.addEventListener('click', (e) => {
            e.preventDefault();
            this.ready(e.currentTarget);
            this.createBtnClose();
            this.showContent();
            this.renderOverlay();
        });
    }

    /**
     * 準備
     * @returns {void}
     */
    ready(target) {
        const id = target.getAttribute('href').replace('#', '');

        this.templateBtnClose = this.body.querySelector(this.o.template.btnCloseSelector);
        this.templateOverlay = this.body.querySelector(this.o.template.overlaySelector);
        this.root = document.getElementById(id);
        this.content = this.root.querySelector(this.o.contentSelector);
    }

    /**
     * 閉じるボタンを作成
     * @returns {void}
     */
    createBtnClose() {
        this.content.appendChild(document.importNode(this.templateBtnClose.content, true));
        this.btnClose = this.root.querySelector(this.o.btnCloseSelector);
    }

    /**
     * オーバーレイを作成
     * @returns {void}
     */
    createOverlay() {
        this.body.appendChild(document.importNode(this.templateOverlay.content, true));
        this.overlay = this.body.querySelector(this.o.overlaySelector);
    }

    /**
     * コンテンツ表示
     * @returns {void}
     */
    showContent() {
        this.addA11y();
        this.bindRemoveEvent();

        this.root.classList.add(this.o.renderClass, this.o.animateClass);
        reflow(this.root);
        this.root.classList.add(this.o.showClass);

        this.root.addEventListener('transitionend', () => {
            this.root.classList.remove(this.o.animateClass);
            this.root.focus();
        }, {
            once: true
        });
    }

    /**
     * オーバーレイ表示
     * @returns {void}
     */
    renderOverlay() {
        const tabindex = new ControlTabindex();

        this.createOverlay();
        this.adjustScrollbarGutter();
        this.html.classList.add(this.o.openClass);

        this.overlay.classList.add(
            this.o.overlay.animateClass,
            this.o.overlay.showClass
        );

        this.overlay.addEventListener('transitionend', () => {
            this.overlay.classList.remove(this.overlay.animateClass);
        }, {
            once: true
        });

        tabindex.add([this.root]);
    }

    /**
     * スクロールバー分の余白調整
     * @returns {void}
     */
    adjustScrollbarGutter() {
        const {innerWidth} = window;
        const {clientWidth} = document.body;

        if (innerWidth !== clientWidth) {
            this.body.style.paddingRight = `${innerWidth - clientWidth}px`;
            this.isAdjustGutter = true;
        }
    }

    /**
     * アクセシビリティ対応
     * @returns {void}
     */
    addA11y() {
        setAttributes(this.root, {
            role: 'dialog',
            tabindex: '0'
        });

        if (this.title) {
            this.addDialogTitle();
        }
    }

    /**
     * ダイアログタイトルを設定
     * @returns {void}
     */
    addDialogTitle() {
        this.root.setAttribute('aria-labelledby', 'dialog-title');
        this.title.setAttribute('id', 'dialog-title');
    }

    /**
     * ダイアログタイトルを削除
     * @returns {void}
     */
    removeDialogTitle() {
        this.root.removeAttribute('aria-labelledby');
        this.title.removeAttribute('id');
    }

    /**
     * コンテンツ非表示のイベント
     * @returns {void}
     */
    bindRemoveEvent() {
        this.bind.remove = this.remove.bind(this);
        this.bind.keydownHandler = this.keydownHandler.bind(this);
        this.bind.stopHandler = Modal.stopHandler.bind(this);

        this.root.addEventListener('click', this.bind.remove);
        this.root.addEventListener('keydown', this.bind.keydownHandler);
        this.btnClose.addEventListener('click', this.bind.remove);
        this.content.addEventListener('click', this.bind.stopHandler);
    }

    /**
     * キーダウンでのモーダル削除
     * @param {Object} e - イベント
     * @returns {void}
     */
    keydownHandler(e) {
        if (e.key === 'Escape') {
            this.remove();
        }
    }

    /**
     * モーダルの削除
     * @returns {void}
     */
    remove() {
        this.hiddenContent();
        this.removeOverlay();
    }

    /**
     * バブリング停止
     * @param {Object} e - イベント
     * @returns {void}
     */
    static stopHandler(e) {
        e.stopPropagation();
    }

    /**
     * コンテンツ非表示
     * @returns {void}
     */
    hiddenContent() {
        this.root.classList.add(this.o.hiddenClass, this.o.animateClass);
        this.root.classList.remove(this.o.showClass);
        this.root.addEventListener('transitionend', () => {
            this.root.classList.remove(this.o.hiddenClass, this.o.animateClass);
        }, {
            once: true
        });

        if (this.o.isIframeVideo) {
            this.reloadIframe();
        }
    }

    /**
     * iframeをリロードして動画再生を強制終了する
     * @returns {void}
     */
    reloadIframe() {
        const item = this.root.querySelector('iframe');

        if (!item) {
            return;
        }

        const src = item.getAttribute('src');

        item.style.visibility = 'hidden';
        item.setAttribute('src', '');
        item.setAttribute('src', src);

        // アニメーション中に処理するとチラつくので実行を遅延
        setTimeout(() => {
            item.style.visibility = '';
        }, 1000);
    }

    /**
     * オーバーレイの削除
     * @returns {void}
     */
    removeOverlay() {
        const tabindex = new ControlTabindex();

        this.overlay.classList.add(this.o.overlay.hiddenClass);
        this.overlay.classList.remove(this.o.overlay.showClass);
        this.overlay.addEventListener('transitionend', () => {
            this.removeComplete();
        });

        tabindex.revert();
    }

    /**
     * 削除後の処理
     * @returns {void}
     */
    removeComplete() {
        if (this.isAdjustGutter) {
            this.body.removeAttribute('style');
            this.isAdjustGutter = false;
        }

        this.html.classList.remove(this.o.openClass);

        this.root.classList.remove(
            this.o.renderClass,
            this.o.hiddenClass,
            this.o.animateClass
        );

        this.root.removeAttribute('tabindex');
        this.root.removeEventListener('click', this.bind.remove);
        this.root.removeEventListener('keydown', this.bind.keydownHandler);
        this.content.removeEventListener('click', this.bind.stopHandler);
        this.overlay.remove();
        this.btnClose.remove();
        this.btn.focus();
        this.removeA11y();
        this.reset();
    }

    /**
     * アクセシビリティの設定を削除
     * @returns {void}
     */
    removeA11y() {
        this.root.removeAttribute('role');

        if (this.title) {
            this.removeDialogTitle();
            this.title = null;
        }
    }
}
