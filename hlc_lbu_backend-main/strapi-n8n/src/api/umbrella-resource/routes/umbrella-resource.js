'use strict';

/**
 * umbrella-resource router
 */

const { createCoreRouter } = require('@strapi/strapi').factories;

module.exports = createCoreRouter('api::umbrella-resource.umbrella-resource');
