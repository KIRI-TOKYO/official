import {setAttributes} from '../helper/setAttributes.js';
import {prop} from '../helper/property.js';

/**
 * タブ切り替え
 */
export class Tab {
    /**
     * @param {Object} root - ルートとなる要素
     * @param {number} index - インデックス
     * @param {Object} [options] - オプション
     */
    constructor(root, index, options = {}) {
        const defaultOptions = {
            listSelector: '.fn-tab_list',
            listItemSelector: '.fn-tab_list_item',
            btnSelector: '.fn-tab_btn',
            panelSelector: '.fn-tab_panel',
            showClass: 'is-show',
            selectClass: 'is-select',
        };

        this.o = Object.assign(defaultOptions, options);
        this.root = root;
        this.list = this.root.querySelector(this.o.listSelector);
        this.listItems = this.list.querySelectorAll(this.o.listItemSelector);
        this.tabs = this.list.querySelectorAll(this.o.btnSelector);
        this.panels = this.root.querySelectorAll(this.o.panelSelector);
        this.noSelect = {
            'aria-selected': false,
            tabindex: '-1',
        };
        this.index = index;
    }

    /**
     * 初期化
     * @returns {void}
     */
    init() {
        this.createTabList();
        this.display();
    }

    /**
     * タブを作成
     * @returns {void}
     */
    createTabList() {
        this.addA11y();

        this.tabs.forEach((tab) => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();

                if (e.currentTarget.getAttribute('aria-selected') === 'false') {
                    this.switch(e.currentTarget);
                }
            });

            tab.addEventListener('keydown', (e) => {
                this.keyCtrl(e, e.currentTarget);
            });
        });
    }

    /**
     * アクセシビリティ対応
     * @returns {void}
     */
    addA11y() {
        const l = this.listItems.length;
        const id = {};
        let i = 0;

        this.list.setAttribute('role', 'tablist');

        for (; i < l; i++) {
            const tab = this.tabs[i];
            const panel = this.panels[i];

            id.panel = panel.getAttribute('id');
            id.tab = `${id.panel}-${this.index}`;

            setAttributes(this.listItems[i], {
                role: 'presentation',
            });

            setAttributes(tab, {
                id: id.tab,
                role: 'tab',
                'aria-controls': id.panel,
            });
            setAttributes(tab, this.noSelect);

            setAttributes(panel, {
                role: 'tabpanel',
                tabindex: '0',
                'aria-labelledby': id.tab,
            });
            prop(panel, 'hidden', true);
        }
    }

    /**
     * 初期表示の処理
     * @returns {void}
     */
    display() {
        let hash = location.hash.replace(/[^\w-]/u, '');
        const select = this.list.querySelector(`.${this.o.selectClass}`);
        let selectTab;
        let id;
        let tab;

        // ハッシュがなければ初期化
        if (!hash.length) {
            hash = null;
        } else {
            id = `#${hash}`;
            tab = this.root.querySelector(id);
        }

        if (hash && tab) {
            // 開いておきたいタブがハッシュで直接指定された場合
            this.switch(
                tab,
                this.root.querySelector(`[aria-labelledby="${hash}"]`),
            );
        } else if (select) {
            // html に直接開いておきたいタブが指定されていた場合
            selectTab = select.querySelector(this.o.btnSelector);

            this.show(
                selectTab,
                this.root.querySelector(`[aria-labelledby="${selectTab.getAttribute('id')}"]`),
            );
        } else {
            this.showFirst();
        }
    }

    /**
     * キーボード操作
     * @param {Object} e - イベント
     * @param {Object} current - アクティブになっているタブ
     * @returns {void}
     */
    keyCtrl(e, current) {
        const {key} = e;
        let target;
        let next;
        let prev;

        if (key === 'ArrowRight' || key === 'ArrowDown') {
            next = current.parentNode.nextElementSibling;

            if (next) {
                target = next.querySelector(this.o.btnSelector);
            } else {
                target = current.parentNode.parentNode.firstElementChild.querySelector(this.o.btnSelector);
            }
        } else if (key === 'ArrowLeft' || key === 'ArrowUp') {
            prev = current.parentNode.previousElementSibling;

            if (prev) {
                target = prev.querySelector(this.o.btnSelector);
            } else {
                target = current.parentNode.parentNode.lastElementChild.querySelector(this.o.btnSelector);
            }
        }

        if (key === 'ArrowLeft' || key === 'ArrowUp' || key === 'ArrowRight' || key === 'ArrowDown') {
            e.preventDefault();
            this.switch(target, true);
        }
    }

    /**
     * 表示切替
     * @param {Object} target - 対象となるタブ
     * @param {boolean} [isKeyboard] - キーボード操作が行われているかの判定
     * @returns {void}
     */
    switch(target, isKeyboard) {
        const selected = this.list.querySelector('[aria-selected="true"]');
        let panel;

        this.removeSelectClass();

        if (selected) {
            panel = document.getElementById(selected.getAttribute('href').replace('#', ''));

            setAttributes(selected, this.noSelect);
            prop(panel, 'hidden', true);
        }

        this.show(
            target,
            this.root.querySelector(`[aria-labelledby="${target.getAttribute('id')}"]`),
        );

        if (isKeyboard) {
            target.focus();
        }
    }

    /**
     * タブのセレクト表示の削除
     * @returns {void}
     */
    removeSelectClass() {
        const selected = this.root.querySelector(`.${this.o.selectClass}`);

        if (selected) {
            selected.classList.remove(this.o.selectClass);
        }
    }

    /**
     * 最初の項目を表示
     * @returns {void}
     */
    showFirst() {
        this.show(this.tabs[0], this.panels[0]);
    }

    /**
     * 表示切替
     * @param {Object} tab - 対象となるタブ
     * @param {Object} panel - 対象となるパネル
     * @returns {void}
     */
    show(tab, panel) {
        setAttributes(tab, {
            'aria-selected': 'true',
            tabindex: '0',
        });
        tab.parentNode.classList.add(this.o.selectClass);
        panel.removeAttribute('hidden');
    }
}
