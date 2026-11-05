'use strict';

/**
 * funnel-flow service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::funnel-flow.funnel-flow');
