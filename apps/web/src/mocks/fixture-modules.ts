import emptyHoldings from "./fixtures/empty/holdings.json";
import emptyOverview from "./fixtures/empty/overview.json";
import emptySeries1Y from "./fixtures/empty/series-1Y.json";
import emptySeriesItd from "./fixtures/empty/series-ITD.json";
import gapAlerts from "./fixtures/gap/alerts.json";
import happyAlerts from "./fixtures/happy/alerts.json";
import happyAuthStatus from "./fixtures/happy/auth-status.json";
import happyBenchmarks from "./fixtures/happy/benchmarks.json";
import happyCatalogs from "./fixtures/happy/catalogs.json";
import happyHealth from "./fixtures/happy/health.json";
import happyHolding1 from "./fixtures/happy/holding-1.json";
import happyHolding1Series1Y from "./fixtures/happy/holding-1-series-1Y.json";
import happyHolding1Series3Y from "./fixtures/happy/holding-1-series-3Y.json";
import happyHolding1Series5Y from "./fixtures/happy/holding-1-series-5Y.json";
import happyHolding1SeriesItd from "./fixtures/happy/holding-1-series-ITD.json";
import happyHolding1Transactions from "./fixtures/happy/holding-1-transactions.json";
import happyHolding2 from "./fixtures/happy/holding-2.json";
import happyHolding2Series1Y from "./fixtures/happy/holding-2-series-1Y.json";
import happyHolding2Series3Y from "./fixtures/happy/holding-2-series-3Y.json";
import happyHolding2Series5Y from "./fixtures/happy/holding-2-series-5Y.json";
import happyHolding2SeriesItd from "./fixtures/happy/holding-2-series-ITD.json";
import happyHolding2Transactions from "./fixtures/happy/holding-2-transactions.json";
import happyHolding3 from "./fixtures/happy/holding-3.json";
import happyHolding3Series1Y from "./fixtures/happy/holding-3-series-1Y.json";
import happyHolding3Series3Y from "./fixtures/happy/holding-3-series-3Y.json";
import happyHolding3Series5Y from "./fixtures/happy/holding-3-series-5Y.json";
import happyHolding3SeriesItd from "./fixtures/happy/holding-3-series-ITD.json";
import happyHolding3Transactions from "./fixtures/happy/holding-3-transactions.json";
import happyHoldings from "./fixtures/happy/holdings.json";
import happyImportResult from "./fixtures/happy/import-result.json";
import happyLoginUrl from "./fixtures/happy/login-url.json";
import happyOverview from "./fixtures/happy/overview.json";
import happyPerformance from "./fixtures/happy/performance.json";
import happySeries1Y from "./fixtures/happy/series-1Y.json";
import happySeries3Y from "./fixtures/happy/series-3Y.json";
import happySeries5Y from "./fixtures/happy/series-5Y.json";
import happySeriesItd from "./fixtures/happy/series-ITD.json";
import happySyncResult from "./fixtures/happy/sync-result.json";
import importErrorsImportReport from "./fixtures/import_errors/import-report.json";
import importErrorsImportResult from "./fixtures/import_errors/import-result.json";
import loggedOutAuthStatus from "./fixtures/logged_out/auth-status.json";
import missingPricesHolding1 from "./fixtures/missing_prices/holding-1.json";
import missingPricesHolding2 from "./fixtures/missing_prices/holding-2.json";
import missingPricesHolding3 from "./fixtures/missing_prices/holding-3.json";
import missingPricesHoldings from "./fixtures/missing_prices/holdings.json";
import missingPricesOverview from "./fixtures/missing_prices/overview.json";
import negativeOverview from "./fixtures/negative/overview.json";
import staleAuthStatus from "./fixtures/stale/auth-status.json";
import unknownCategoryBenchmarks from "./fixtures/unknown_category/benchmarks.json";
import unknownCategoryHolding3 from "./fixtures/unknown_category/holding-3.json";
import unknownCategoryHoldings from "./fixtures/unknown_category/holdings.json";

export const fixtureModules: Record<string, unknown> = {
  "./fixtures/empty/holdings.json": emptyHoldings,
  "./fixtures/empty/overview.json": emptyOverview,
  "./fixtures/empty/series-1Y.json": emptySeries1Y,
  "./fixtures/empty/series-ITD.json": emptySeriesItd,
  "./fixtures/gap/alerts.json": gapAlerts,
  "./fixtures/happy/alerts.json": happyAlerts,
  "./fixtures/happy/auth-status.json": happyAuthStatus,
  "./fixtures/happy/benchmarks.json": happyBenchmarks,
  "./fixtures/happy/catalogs.json": happyCatalogs,
  "./fixtures/happy/health.json": happyHealth,
  "./fixtures/happy/holding-1.json": happyHolding1,
  "./fixtures/happy/holding-1-series-1Y.json": happyHolding1Series1Y,
  "./fixtures/happy/holding-1-series-3Y.json": happyHolding1Series3Y,
  "./fixtures/happy/holding-1-series-5Y.json": happyHolding1Series5Y,
  "./fixtures/happy/holding-1-series-ITD.json": happyHolding1SeriesItd,
  "./fixtures/happy/holding-1-transactions.json": happyHolding1Transactions,
  "./fixtures/happy/holding-2.json": happyHolding2,
  "./fixtures/happy/holding-2-series-1Y.json": happyHolding2Series1Y,
  "./fixtures/happy/holding-2-series-3Y.json": happyHolding2Series3Y,
  "./fixtures/happy/holding-2-series-5Y.json": happyHolding2Series5Y,
  "./fixtures/happy/holding-2-series-ITD.json": happyHolding2SeriesItd,
  "./fixtures/happy/holding-2-transactions.json": happyHolding2Transactions,
  "./fixtures/happy/holding-3.json": happyHolding3,
  "./fixtures/happy/holding-3-series-1Y.json": happyHolding3Series1Y,
  "./fixtures/happy/holding-3-series-3Y.json": happyHolding3Series3Y,
  "./fixtures/happy/holding-3-series-5Y.json": happyHolding3Series5Y,
  "./fixtures/happy/holding-3-series-ITD.json": happyHolding3SeriesItd,
  "./fixtures/happy/holding-3-transactions.json": happyHolding3Transactions,
  "./fixtures/happy/holdings.json": happyHoldings,
  "./fixtures/happy/import-result.json": happyImportResult,
  "./fixtures/happy/login-url.json": happyLoginUrl,
  "./fixtures/happy/overview.json": happyOverview,
  "./fixtures/happy/performance.json": happyPerformance,
  "./fixtures/happy/series-1Y.json": happySeries1Y,
  "./fixtures/happy/series-3Y.json": happySeries3Y,
  "./fixtures/happy/series-5Y.json": happySeries5Y,
  "./fixtures/happy/series-ITD.json": happySeriesItd,
  "./fixtures/happy/sync-result.json": happySyncResult,
  "./fixtures/import_errors/import-report.json": importErrorsImportReport,
  "./fixtures/import_errors/import-result.json": importErrorsImportResult,
  "./fixtures/logged_out/auth-status.json": loggedOutAuthStatus,
  "./fixtures/missing_prices/holding-1.json": missingPricesHolding1,
  "./fixtures/missing_prices/holding-2.json": missingPricesHolding2,
  "./fixtures/missing_prices/holding-3.json": missingPricesHolding3,
  "./fixtures/missing_prices/holdings.json": missingPricesHoldings,
  "./fixtures/missing_prices/overview.json": missingPricesOverview,
  "./fixtures/negative/overview.json": negativeOverview,
  "./fixtures/stale/auth-status.json": staleAuthStatus,
  "./fixtures/unknown_category/benchmarks.json": unknownCategoryBenchmarks,
  "./fixtures/unknown_category/holding-3.json": unknownCategoryHolding3,
  "./fixtures/unknown_category/holdings.json": unknownCategoryHoldings,
};
