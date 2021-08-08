/**
 * 属性複数付与
 * @param {Object} el - 対象の要素
 * @param {Object} attrs - 属性とその値
 */
export const setAttributes = (el, attrs) => {
    for (const key in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, key)) {
            el.setAttribute(key, attrs[key]);
        }
    }
};
