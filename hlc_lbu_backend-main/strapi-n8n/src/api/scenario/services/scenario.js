'use strict';

/**
 * scenario service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::scenario.scenario');
