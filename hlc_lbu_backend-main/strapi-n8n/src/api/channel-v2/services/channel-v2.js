'use strict';

/**
 * channel-v2 service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::channel-v2.channel-v2');
