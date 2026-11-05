'use strict';

/**
 * funnel service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::funnel.funnel');
