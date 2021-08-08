import {mediaQuery} from "../config/mediaQuery.js";
import {setAttributes} from '../helper/setAttributes.js';
import {setTabindex} from '../helper/setTabindex.js';

/**
 * メニュー
 */
export class Menu {
    /**
     *
     * @param {Object} root - ルートとなる要素
     * @param {Object} [options] - オプション
     */
    constructor(root, options = {}) {
        const defaultOptions = {
            template: {
                btnSelector: '.fn-menu_template-btn',
            },
            contentSelector: '.fn-menu_content',
            btnSelector: '.fn-menu_btn',
            overlaySelector: '.fn-menu_overlay',
            id: 'menu',
            animateClass: 'is-animate',
            showClass: 'is-show',
            menuShowClass: 'is-menu-show',
        };

        this.o = Object.assign(defaultOptions, options);
        this.root = root;
        this.content = this.root.querySelector(this.o.contentSelector);
        this.templateBtn = this.root.querySelector(this.o.template.btnSelector);
        this.btn = null;
        this.header = document.querySelector('.header');
    }

    /**
     * 初期化
     * @returns {void}
     */
    init() {
        this.switch();
        this.onMatch();
    }

    /**
     * ボタンの作成
     * @returns {void}
     */
    createBtn() {
        this.content.before(document.importNode(this.templateBtn.content, true));
        this.btn = this.root.querySelector(this.o.btnSelector);

        this.addA11y();
        this.bindEvent();
    }

    /**
     * アクセシビリティ対応
     * @returns {void}
     */
    addA11y() {
        setAttributes(this.btn, {
            'aria-controls': this.o.id,
            'aria-expanded': 'false',
        });
        this.content.setAttribute('id', this.o.id);
    }

    /**
     * イベントの登録
     * @returns {void}
     */
    bindEvent() {
        this.btn.addEventListener('click', () => {
            if (this.isExpand()) {
                this.collapse();
            } else {
                this.expand();
            }
        });
    }

    /**
     * 開閉の確認
     * @returns {boolean}
     */
    isExpand() {
        return this.btn.getAttribute('aria-expanded') === 'true';
    }

    /**
     * 開く
     * @returns {void}
     */
    expand() {
        const tabindex = new setTabindex();

        this.btn.setAttribute('aria-expanded', 'true');
        this.content.classList.add(this.o.animateClass, this.o.showClass);
        this.header.classList.add(this.o.menuShowClass);

        this.content.addEventListener('transitionend', () => {
            this.content.classList.remove(this.o.animateClass);
            tabindex.add([this.header]);
        }, {
            once: true,
        });
    }

    /**
     * 閉じる
     * @returns {void}
     */
    collapse() {
        this.btn.setAttribute('aria-expanded', 'false');
        this.content.classList.add(this.o.animateClass);
        this.header.classList.remove(this.o.menuShowClass);

        this.content.addEventListener('transitionend', () => {
            const tabindex = new setTabindex();

            tabindex.revert();
            this.content.classList.remove(this.o.animateClass, this.o.showClass);
        }, {
            once: true,
        });
    }

    /**
     * 機能停止
     * @returns {void}
     */
    destroy() {
        this.btn.remove();
        this.btn = null;

        this.content.removeAttribute('id');
        this.content.classList.remove(this.o.showClass);
        this.header.classList.remove(this.o.menuShowClass);
    }

    /**
     * メディアクエリの監視
     * @returns {void}
     */
    onMatch() {
        mediaQuery[0].addListener(() => {
            this.switch();
        })
    }

    /**
     * 機能の切り替え
     * @returns {void}
     */
    switch() {
        const isMatch = mediaQuery[0].matches;

        if (isMatch && !this.btn) {
            this.createBtn()
        } else if (!isMatch && this.btn) {
            this.destroy();
        }
    }
}
