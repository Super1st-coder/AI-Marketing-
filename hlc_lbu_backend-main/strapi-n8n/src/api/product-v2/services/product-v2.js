'use strict';

/**
 * product-v2 service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::product-v2.product-v2');
