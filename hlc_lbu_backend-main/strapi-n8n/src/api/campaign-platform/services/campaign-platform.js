'use strict';

/**
 * campaign-platform service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::campaign-platform.campaign-platform');
