import {focusable} from '../config/focusable.js';

/**
 * tabindexの操作
 */
export class ControlTabindex {
    constructor() {
        this.focusable = document.querySelectorAll(focusable);
        this.tabindexClass = 'was-tabindex';
        this.excludeClass = 'is-exclude';
    }

    /**
     * tabindexを付与
     * @param {[]} [exclude] - 対象外とする要素
     * @returns {void}
     */
    add(exclude) {
        this.focusable.forEach((target) => {
            const val = target.getAttribute('tabindex');

            if (val) {
                target.dataset.tabindex = val;
                target.classList.add(this.tabindexClass);
            }

            target.setAttribute('tabindex', '-1');
        });

        if (exclude) {
            this.revert(exclude);
        }
    }

    /**
     * tabindexの状態を戻す
     * @param {[]} [exclude] - 対象外とする要素
     * @returns {void}
     */
    revert(exclude) {
        if (exclude) {
            const l = exclude.length;
            let i = 0;

            for (; i < l; i++) {
                exclude[i].querySelectorAll(focusable).forEach((target) => {
                    this.remove(target);
                    target.classList.add(this.excludeClass);
                });
            }
        } else {
            this.focusable.forEach((target) => {
                this.remove(target);
            });
        }
    }

    /**
     * 付与したtabindexの削除
     * @param {Object} target - 操作する要素
     * @returns {void}
     */
    remove(target) {
        const wasTabindex = target.classList.contains(this.tabindexClass);

        if (target.classList.contains(this.excludeClass)) {
            target.classList.remove(this.excludeClass);

            return;
        }

        if (wasTabindex) {
            target.setAttribute('tabindex', target.dataset.tabindex);
            target.classList.remove(this.tabindexClass);
            delete target.dataset.tabindex;
        } else {
            target.removeAttribute('tabindex');
        }
    }
}
