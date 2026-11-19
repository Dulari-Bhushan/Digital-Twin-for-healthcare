// Which country the demo is set in (JP or IN), told by the server (/api/clinic). It changes the local emergency number and a few food
// examples in fixed texts. Numbers that come from the patient's data are never touched: swaps are done on the text before values are filled in.
export const region = { current: 'JP' }
export const setRegion = (r) => { region.current = r === 'IN' ? 'IN' : 'JP' }
const NUMBER = { JP: '119', IN: '108' }
const FOOD = { JP: [['rice and roti', 'rice and bread'], ['vegetables and dal', 'vegetables and protein'], ['A quarter less rice and roti', 'A quarter less rice or bread']], IN: [] }

/** The local emergency number in a fixed text of any language. */
export const withNumber = (text, r = region.current) => text.replace(/(?<!\d)(108|119)(?!\d)/g, NUMBER[r])
/** A fixed English text with the local emergency number and foods. */
export const L = (text, r = region.current) => FOOD[r].reduce((s, [a, b]) => s.split(a).join(b), withNumber(text, r))
