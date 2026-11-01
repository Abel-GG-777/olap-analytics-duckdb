import {analytics} from './analytics.js';
globalThis.olapAnalytics=analytics;
await import('../app/static/app.js');
