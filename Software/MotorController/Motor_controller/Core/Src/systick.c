/*
 * systick.c
 *
 *  Created on: May 12, 2025
 *      Author: PANKAJA
 */

#include "systick.h"
#include "encoders.h"
#include "kinematics.h"

// Control loop counter

void CheckEncoderCounts(void) {
    // Check for encoder overflow and reset if necessary
    if (getForwardLeftEncoderCounts() > 30000 || getForwardRightEncoderCounts() > 30000 ||
        getRearLeftEncoderCounts() > 30000 || getRearRightEncoderCounts() > 30000 ||
        getForwardLeftEncoderCounts() < -30000 || getForwardRightEncoderCounts() < -30000 ||
        getRearLeftEncoderCounts() < -30000 || getRearRightEncoderCounts() < -30000) {

        // Reset encoders to prevent overflow
        resetEncodersinSystick();
    }
}

void SysTickFunction(void) {
    /*
     * This function is called every millisecond (1kHz)
     * Main control loop for the Omni-Dorectional robot
     */

//    control_counter++;
//
//    // Check for encoder overflow every 100ms
//    if (control_counter % 100 == 0) {
//        CheckEncoderCounts();
//    }
//
//    // Update kinematics control every millisecond
//    update_kinematics_control();
//
//    // Update demo sequence
//    update_demo_sequence();
    /*
    if (control_counter % 1000 == 0) {
        // Print current velocities or other debug info
        // printf("vx: %.2f, vy: %.2f, wz: %.2f\n",
        //        current_robot_velocity.vx,
        //        current_robot_velocity.vy,
        //        current_robot_velocity.wz);
    }
    */
}
