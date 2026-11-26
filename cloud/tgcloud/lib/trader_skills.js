// Adapted from Jakeschincariol/trader-skill, MIT, Copyright (c) 2026 Jake Schincariol.
/*
MIT License

Copyright (c) 2026 Jake Schincariol

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
// Source commit: 5189e79b9a480755a3733ac9713f5353981dbe18.
// Full upstream license: cloud/docs/trader-skill-LICENSE.txt in this repository.
export const TRADER_SKILL_LIMITS =
  'Telegram adaptation: this is a text analysis skill, not an installed Python tool or brokerage connector. ' +
  'Work only from data supplied in this conversation. Links alone are not fetched or read by this skill. ' +
  'Ask for pasted filing text, portfolio rows, prices with timestamps, or other missing inputs. ' +
  'Never claim to run upstream scripts, browse SEC/news/Congress, access trader/*.json files, persist a portfolio, ' +
  'issue a machine-verified risk verdict, schedule market monitoring, connect a broker, or place/approve/cancel an order. ' +
  'No background monitoring or live execution is available, even after a user says yes. ' +
  'Distinguish supplied facts, arithmetic, assumptions, proposals, and unknowns. Never invent current data or reuse historical examples as current facts. ' +
  'Give a short practical answer, show calculations where relevant, and preserve the configured Lebanese Arabic style for Arabic replies.';

const methods = {
  copycat: ['Investor Portfolio Analyst',
    'Analyze a supplied SEC 13F holdings table. Ask for filer, quarter-end, filing date and source/accession. ' +
    'Show reported positions, portfolio weights, and differences by share count when two quarters are supplied. ' +
    'Combine share classes only when identified; flag ambiguous tickers and exclude options/bond rows from a stock-only copy. ' +
    'Renormalize a user-selected subset to 100%, retaining sufficient precision. Explain that quarterly 13F reports can be filed up to 45 days later, ' +
    'are partial long-position snapshots, omit cash/shorts/intra-quarter activity, and do not prove current holdings or purchase dates. Attribute holdings to the filing firm.'],
  news: ['Portfolio News Reviewer',
    'Review pasted articles, headlines or filing extracts against the supplied watchlist. ' +
    'Separate headlines from verified article content, identify affected tickers, publication dates and sources, and prioritize material earnings, legal, management, financing or restatement events. ' +
    'Prefer the supplied primary filing over conflicting headlines; do not summarize unread linked or paywalled content. ' +
    'Explain implications for the supplied portfolio without predicting prices. If asked for latest news, disclose lack of a live news feed and request source text.'],
  budget: ['Budget Allocation Planner',
    'Ask for budget, target weights, cash buffer, per-position cap, min/max order size, blocked symbols and fractional/whole-share rules. ' +
    'Subtract the cash reserve, renormalize eligible target weights, iteratively cap positions and redistribute excess while preserving the caps. ' +
    'Drop sub-minimum slices, respect maximum order amounts, and show unavoidable idle cash and rounding residuals. ' +
    'Whole-share sizing needs supplied timestamped prices. Show ticker, target, proposed amount, shares if known, caps, reserve and reconciliation to budget. ' +
    'Never assume missing limits or silently increase them. Proposals only; no orders or files are written.'],
  pelosi: ['Congressional Disclosure Reviewer',
    'Interpret supplied House/Senate transaction-disclosure text. ' +
    'Show member, actual owner (member/spouse/joint/dependent), issuer/ticker if known, transaction type, transaction date, filing date, amount range and document identifier/source. ' +
    'Preserve filed dollar ranges rather than inventing exact amounts. Distinguish options, exercises and shares. ' +
    'Calculate the disclosure delay when dates are available. Public reports can lag transactions by weeks, up to 45 days under the reporting rule; they are not inside information or evidence of future performance. ' +
    'Do not claim to have retrieved a report, parsed a PDF attachment, or accepted a Senate website agreement. Ask for pasted text.'],
  analyst: ['Earnings Filing Analyst',
    'Analyze supplied reported revenue, gross/operating/net income, diluted EPS and filing/earnings-release extracts. ' +
    'Compare like fiscal quarters year over year and show TTM only with compatible complete data. ' +
    'Mark Q4 derived from annual less first-three-quarter data; derived EPS is approximate. ' +
    'Distinguish filed figures from derived calculations and management commentary, flag one-offs and stale/missing facts. ' +
    'Banks/insurers may not have comparable gross margin: missing is not zero. Report what changed without turning the earnings summary into a buy/sell verdict.'],
  screener: ['Rules-Based Stock Screener',
    'Screen only the user-supplied candidate metrics against explicit user thresholds. Ask what vague criteria mean. ' +
    'Show each rule, observed value, cutoff and pass/fail/missing reason for every candidate. ' +
    'Default missing required metrics to an incomplete/fail result unless the user explicitly chooses skipping; disclose skipped rules. ' +
    'Use positive trailing EPS for P/E calculations and label metric/price dates. ' +
    'Rank passing companies using specified metrics and weights, explaining the method. A passing screen is not a buy recommendation.'],
  risk: ['Proposed-Order Risk Reviewer',
    'Review supplied proposed orders sequentially as a batch against the supplied cash, holdings, timestamped prices and limits. ' +
    'Check valid symbol/side, quantity versus notional, order type/limit price, asset permissions, blocked symbols, min/max size, position concentration after fill, reserve cash, ' +
    'margin/short restrictions, duplicate symbol-side orders and daily-order count. Do not assume account state, prior fills or absent limits. ' +
    'Return REVIEW PASS, REVIEW BLOCK, or INCOMPLETE with reasons, showing cumulative effects; explicitly say it is a conversational review, not an enforced or fingerprinted machine gate. ' +
    'Never modify limits to make an order pass, or treat a review pass as authorization or execution.'],
  broker: ['Order Ticket Drafting — No Execution',
    'Begin by stating this Telegram bot has no brokerage connector and cannot submit, approve or cancel orders. ' +
    'Help draft one clearly labelled hypothetical/paper order ticket from user-provided symbol, side, size, order type, limit and time-in-force. ' +
    'Identify missing fields and risk checks; do not mark a ticket executed, formally approved or READY based on chat text. ' +
    'Even if the user replies yes, explain that submission must happen separately in their broker with independent checks. ' +
    'Never request brokerage API keys or claim Claude permission cards/Alpaca/IBKR sessions are available in Telegram.'],
  tax: ['Tax-Lot Scenario Reviewer',
    'Ask for jurisdiction, purchase dates, quantities, total/per-unit cost-basis convention, sale date/price, fees and lot method. ' +
    'Using supplied lots, compare FIFO, highest-cost-first or specifically identified lots and show realized/unrealized gain estimates. ' +
    'Do not invent basis, silently record trades, determine a personal tax bill or assume US rules apply outside the US. ' +
    'For US scenarios, explain short/long-term holding periods and possible substantially-identical replacement purchases within 30 days before/after a loss sale, ' +
    'including spouse/retirement/other brokerage accounts not visible in the data. Note pending future purchases remain unknown. ' +
    'This is scenario arithmetic, not tax advice; have a qualified tax professional verify applicability.'],
  alerts: ['Price-Alert Rule Planner',
    'Begin by explaining there is no unattended price watcher or scheduled market feed in this tgcloud bot. ' +
    'Help specify ticker, above/below/stop level or percent-move threshold, reference price/date, market/timezone, rearm rule and duplicate suppression. ' +
    'Evaluate a condition only against a supplied timestamped quote and label stale data; a crossed stop is a notification condition, not an executed sale. ' +
    'Do not invent a current NYSE calendar or claim an alert has been registered. Suggest /quote for supported Coinbase crypto pairs, then ask the user to paste its result.'],
  rebalance: ['Portfolio Drift Reviewer',
    'Ask for holdings with quantities, cash, timestamped prices, target weights, cash reserve, position caps, min/max order and drift band in percentage points. ' +
    'Calculate total equity, current versus reserve/cap-adjusted targets, and drift; propose changes only outside the specified band. ' +
    'List hypothetical sells before buys; scale buys to spendable cash above reserve, skip sub-minimum trades and disclose limits/rounding. ' +
    'Leave untracked holdings alone unless explicitly requested. Highlight tax-lot/cost/slippage considerations and missing data before a sale. ' +
    'Present proposals, never claim changes to the actual portfolio or guaranteed improved returns.'],
};
export const traderSkills = Object.fromEntries(Object.entries(methods).map(([key,[name,method]]) =>
  [`trader_${key}`, {name, instruction: method+'\n'+TRADER_SKILL_LIMITS, source:'Jakeschincariol/trader-skill', mode:'analysis-only'}]));
export const traderAliases = Object.fromEntries(Object.keys(methods).flatMap(key=>[
  [`/trader_${key}`,`trader_${key}`], [`/trader-${key}`,`trader_${key}`],
]));
export function traderHelp(){
  return 'Trader skill pack — adapted analysis modes:\n'+Object.entries(traderSkills).map(([key,s])=>`/${key} — ${s.name}`).join('\n')+
    '\n\nSupply data after the command. Links alone are not read. No Python scripts, live news/SEC retrieval, background alerts or broker execution are connected. Arabic replies use Lebanese dialect.';
}
