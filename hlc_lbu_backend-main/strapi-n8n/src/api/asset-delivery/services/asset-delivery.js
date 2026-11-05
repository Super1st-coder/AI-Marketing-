'use strict';

/**
 * asset-delivery service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::asset-delivery.asset-delivery');
