/**
 * プロパティのチェック、変更
 * @param {Object} target - プロパティを調査したい要素
 * @param {Object} name - プロパティ名
 * @param {*} [val] - 値
 * @returns {*}
 */
export const prop = (target, name, val) => {
    if (!val) {
        return target[name];
    }

    return (target[name] = val);
};
