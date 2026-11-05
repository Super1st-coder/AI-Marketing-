'use strict';

/**
 * hypothesis service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::hypothesis.hypothesis');
