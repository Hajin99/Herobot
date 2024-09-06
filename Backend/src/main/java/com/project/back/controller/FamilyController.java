package com.project.back.controller;

import com.project.back.dto.FamilyRequestDTO;
import com.project.back.dto.FamilyUserDTO;
import com.project.back.entity.FamilyRequest;
import com.project.back.entity.Familyship;
import com.project.back.entity.UserEntity;
import com.project.back.repository.UserRepository;
import com.project.back.service.FamilyService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/family")
@RequiredArgsConstructor
public class FamilyController {
    private final FamilyService familyService;
    private final UserRepository userRepository;  // UserRepository를 주입받습니다.

    @PostMapping("/request")
    public FamilyRequest sendFamilyRequest(@RequestBody FamilyRequestDTO request) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String senderUsername = authentication.getName();  // 현재 로그인한 사용자의 username

        UserEntity sender = userRepository.findByUsername(senderUsername);
        if (sender == null) {
            throw new RuntimeException("User not found");
        }
        Long senderId = sender.getId();  // UserEntity에서 ID를 얻습니다.

        // request.getUsername()을 호출할 때 null 확인
        String receiverUsername = request.getUsername();
        if (receiverUsername == null || receiverUsername.isEmpty()) {
            throw new RuntimeException("Receiver username is required");
        }

        return familyService.sendFamilyRequest(senderId, receiverUsername);
    }


    // URL 쿼리 파라미터 http://localhost:8080/family/accept?requestId=2902 형식으로 요청받음
    @PostMapping("/accept")
    public ResponseEntity<Familyship> acceptFamilyRequest(@RequestParam(name = "requestId", required = false) Long requestId) {
        System.out.println("Request ID: " + requestId); // 디버깅 로그
        try {
            Familyship familyship = familyService.acceptFamilyRequest(requestId);
            return ResponseEntity.ok(familyship);
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @GetMapping("/list")
    public List<FamilyUserDTO> geetFamily(){
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String username = authentication.getName();  // 현재 로그인한 사용자의 username

        UserEntity user = userRepository.findByUsername(username);
        if (user == null) {
            throw new RuntimeException("User not found");
        }

        List<UserEntity> family = familyService.getFamily(user.getId());
        return family.stream()
                .map(familyName -> new FamilyUserDTO(familyName.getNickname(), familyName.getPhotoname()))
                .collect(Collectors.toList());
    }

    //사용자가 보낸 친구 요청들을 조회
    @GetMapping("/requests/sent")
    public List<FamilyRequestDTO> getSentRequests() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String senderUsername = authentication.getName();  // 현재 로그인한 사용자의 username

        UserEntity sender = userRepository.findByUsername(senderUsername);
        if (sender == null) {
            throw new RuntimeException("User not found");
        }

        List<FamilyRequest> sentRequests = familyService.getSentRequests(sender.getId());
        return sentRequests.stream()
                .map(request -> new FamilyRequestDTO(request.getReceiver().getUsername()))
                .collect(Collectors.toList());
    }

    //사용자가 받은 친구 요청들을 조회
    @GetMapping("/requests/received")
    public List<FamilyRequestDTO> getReceivedRequests() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String receiverUsername = authentication.getName();  // 현재 로그인한 사용자의 username

        UserEntity receiver = userRepository.findByUsername(receiverUsername);
        if (receiver == null) {
            throw new RuntimeException("User not found");
        }

        List<FamilyRequest> receivedRequests = familyService.getReceivedRequests(receiver.getId());
        return receivedRequests.stream()
                .map(request -> new FamilyRequestDTO(request.getSender().getUsername()))
                .collect(Collectors.toList());
    }


//    @GetMapping("/list")
//    public List<UserEntity> getFamily() {
//        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
//        String username = authentication.getName();  // 현재 로그인한 사용자의 username
//
//        UserEntity user = userRepository.findByUsername(username);
//        if (user == null) {
//            throw new RuntimeException("User not found");
//        }
//
//        return familyService.getFamily(user.getId());
//    }
//@GetMapping("/requests/sent")
//public List<FamilyRequest> getSentRequests() {
//    Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
//    String senderUsername = authentication.getName();  // 현재 로그인한 사용자의 username
//
//    UserEntity sender = userRepository.findByUsername(senderUsername);
//    if (sender == null) {
//        throw new RuntimeException("User not found");
//    }
//
//    return familyService.getSentRequests(sender.getId());
//}
//

//    @GetMapping("/requests/received")
//    public List<FamilyRequest> getReceivedRequests() {
//        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
//        String receiverUsername = authentication.getName();  // 현재 로그인한 사용자의 username
//
//        UserEntity receiver = userRepository.findByUsername(receiverUsername);
//        if (receiver == null) {
//            throw new RuntimeException("User not found");
//        }
//
//        return familyService.getReceivedRequests(receiver.getId());
//    }
}

