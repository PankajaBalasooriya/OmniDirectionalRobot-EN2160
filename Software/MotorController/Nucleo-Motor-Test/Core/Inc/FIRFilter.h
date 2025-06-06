/*
 * FIRFilter.h
 *
 *  Created on: Apr 26, 2025
 *      Author: PANKAJA
 */

#ifndef INC_FIRFILTER_H_
#define INC_FIRFILTER_H_

#ifndef FIR_FILTER_H
#define FIR_FILTER_H

#include <stdint.h>

#define FIR_FILTER_LENGTH 20

typedef struct {
	float 	buf[FIR_FILTER_LENGTH];
	uint8_t bufIndex;

	float out;
} FIRFilter;

void FIRFilter_Init(FIRFilter *fir);
float FIRFilter_Update(FIRFilter *fir, float inp);

#endif

#endif /* INC_FIRFILTER_H_ */
