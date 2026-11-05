'use strict';

/**
 * scenario router
 */

const { createCoreRouter } = require('@strapi/strapi').factories;

module.exports = createCoreRouter('api::scenario.scenario');
