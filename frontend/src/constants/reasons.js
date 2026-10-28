/**
 * 举报原因（6 项）与拒绝原因（6 项）兜底字典。
 * 运行时以 GET /api/meta 的 report_reasons / reject_reasons 为准。
 */

export const REPORT_REASONS = [
  { code: 'false_claim', label: '虚假宣传' },
  { code: 'expired_info', label: '过期信息' },
  { code: 'price_wrong', label: '价格不实' },
  { code: 'suspicious_link', label: '链接可疑' },
  { code: 'inappropriate', label: '不当内容' },
  { code: 'other', label: '其他' },
];

export const REJECT_REASONS = [
  { code: 'false_claim', label: '虚假宣传或夸大功效' },
  { code: 'incomplete', label: '信息不完整或不实' },
  { code: 'bad_link', label: '链接不可访问或可疑' },
  { code: 'image_mismatch', label: '图片与内容不符' },
  { code: 'banned_industry', label: '禁投行业或违禁品' },
  { code: 'other', label: '其他（需说明）' },
];

/**
 * 按 code 取中文标签。
 * @param {Array<{code:string,label:string}>} list
 * @param {string} code
 * @returns {string}
 */
export function labelOf(list, code) {
  if (!Array.isArray(list)) return code || '';
  const found = list.find((item) => item && item.code === code);
  return found ? found.label : code || '';
}

export default REPORT_REASONS;
